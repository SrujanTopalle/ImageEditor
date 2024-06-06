""" QtImageViewer.py: PyQt image viewer widget based on QGraphicsView with mouse zooming/panning and ROIs.
"""

import os.path

from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import Qt, QRect, QRectF, QPoint, QPointF, pyqtSignal, QEvent, QSize
from PyQt6.QtGui import QImage, QPixmap, QPainterPath, QMouseEvent, QPainter, QPen
from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QFileDialog, QSizePolicy, \
    QGraphicsItem, QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsLineItem, QGraphicsPolygonItem

from PIL import Image, ImageFilter, ImageDraw
from PIL.ImageQt import ImageQt

class QtImageViewer(QGraphicsView):
    
    # Mouse button signals emit image scene (x, y) coordinates.
    # !!! For image (row, column) matrix indexing, row = y and column = x.
    # !!! These signals will NOT be emitted if the event is handled by an interaction such as zoom or pan.
    # !!! If aspect ratio prevents image from filling viewport, emitted position may be outside image bounds.
    leftMouseButtonPressed = pyqtSignal(float, float)
    leftMouseButtonReleased = pyqtSignal(float, float)
    middleMouseButtonPressed = pyqtSignal(float, float)
    middleMouseButtonReleased = pyqtSignal(float, float)
    rightMouseButtonPressed = pyqtSignal(float, float)
    rightMouseButtonReleased = pyqtSignal(float, float)
    leftMouseButtonDoubleClicked = pyqtSignal(float, float)
    rightMouseButtonDoubleClicked = pyqtSignal(float, float)

    # Emitted upon zooming/panning.
    viewChanged = pyqtSignal()

    # Emitted on mouse motion.
    # Emits mouse position over image in image pixel coordinates.
    # !!! setMouseTracking(True) if you want to use this at all times.
    mousePositionOnImageChanged = pyqtSignal(QPoint)

    # Emit index of selected ROI
    roiSelected = pyqtSignal(int)

    def __init__(self, parent):
        QGraphicsView.__init__(self)
        
        self.parent = parent

        # Image is displayed as a QPixmap in a QGraphicsScene attached to this QGraphicsView.
        self.scene = QGraphicsScene()
        self.setScene(self.scene)

        # Better quality pixmap scaling?
        # self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)

        # Displayed image pixmap in the QGraphicsScene.
        self._current_filename = None
        self._image = None

        # Image aspect ratio mode.
        #   Qt.IgnoreAspectRatio: Scale image to fit viewport.
        #   Qt.KeepAspectRatio: Scale image to fit inside viewport, preserving aspect ratio.
        #   Qt.KeepAspectRatioByExpanding: Scale image to fill the viewport, preserving aspect ratio.
        self.aspectRatioMode = Qt.AspectRatioMode.KeepAspectRatio

        # Scroll bar behaviour.
        #   Qt.ScrollBarAlwaysOff: Never shows a scroll bar.
        #   Qt.ScrollBarAlwaysOn: Always shows a scroll bar.
        #   Qt.ScrollBarAsNeeded: Shows a scroll bar only when zoomed.
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Interactions (set buttons to None to disable interactions)
        # !!! Events handled by interactions will NOT emit *MouseButton* signals.
        #     Note: regionZoomButton will still emit a *MouseButtonReleased signal on a click (i.e. tiny box).
        self.regionZoomButton = Qt.MouseButton.LeftButton  # Drag a zoom box.
        self.zoomOutButton = Qt.MouseButton.RightButton # Pop end of zoom stack (double click clears zoom stack).
        self.panButton = Qt.MouseButton.MiddleButton  # Drag to pan.
        self.wheelZoomFactor = 1.25  # Set to None or 1 to disable mouse wheel zoom.
        self.zoomLevel = 1

        # Stack of QRectF zoom boxes in scene coordinates.
        # !!! If you update this manually, be sure to call updateViewer() to reflect any changes.
        self.zoomStack = []

        # Flags for active zooming/panning.
        self._isZooming = False
        self._isPanning = False

        self._isLeftMouseButtonPressed = False

        # Flags for color picking
        self._isColorPicking = False

        # Flags for painting
        self._isPainting = False
        self.paintBrushSize = 43

        # Flags for filling
        self._isFilling = False

        # Flags for rectangle select
        # Set to true when using the rectangle select tool with toolbar
        self._isSelectingRect = False
        self._isSelectingRectStarted = False
        self._selectRectItem = None
        self._selectRect = None

        # Flags for active selecting
        # Set to true when using the select tool with toolbar
        self._isSelectingPath = False
        self.selectPoints = []
        self.path = None
        self.pathSelected = None
        self.selectPainterPaths = []
        self.pathItem = None
        self.pathPointItem = None
        self.selectPainterPointPaths = []

        self._isCropping = False

        # Flags for spot removal tool
        self._isRemovingSpots = False
        self._targetSelected = False
        self._sourcePos = None
        self._targetPos = None
        self.spotsBrushSize = 10
        self.spotRemovalSimilarityThreshold = 10

        # Flags for blur tool
        self._isBlurring = False
        self.blurBrushSize = 43

        # Flags for erasing
        self._isErasing = False
        self.eraserBrushSize = 43

        # Store temporary position in screen pixels or scene units.
        self._pixelPosition = QPoint()
        self._scenePosition = QPointF()
        self._lastMousePositionInScene = QPointF()

        # Track mouse position. e.g., For displaying coordinates in a UI.
        self.setMouseTracking(True)

        # ROIs.
        self.ROIs = []

        # # For drawing ROIs.
        # self.drawROI = None

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # self.OriginalImage = None

        self.ColorPicker = None

        ##############################################################################################
        ##############################################################################################
        # Layers
        ##############################################################################################
        ##############################################################################################

        self.layerHistory = {
            0: []    
        }
        self.currentLayer = 0
        self.numLayersCreated = 1

        self.checkerBoard = None
        self.checkerBoardWidth = 0
        self.checkerBoardHeight = 0

        # Reference to dock widget that shows layer list
        self.layerListDock = None

    def sizeHint(self):
        return QSize(900, 600)

    def hasImage(self):
        """ Returns whether the scene contains an image pixmap.
        """
        return self._image is not None

    def clearImage(self):
        """ Removes the current image pixmap from the scene if it exists.
        """
        if self.hasImage():
            self.scene.removeItem(self._image)
            self._image = None

    def pixmap(self):
        """ Returns the scene's current image pixmap as a QPixmap, or else None if no image exists.
        :rtype: QPixmap | None
        """
        if self.hasImage():
            return self._image.pixmap()
        return None

    def currentPixmapSize(self):
        pixmap = self.pixmap()
        if pixmap:
            return pixmap.size()
        else:
            return None

    def image(self):
        """ Returns the scene's current image pixmap as a QImage, or else None if no image exists.
        :rtype: QImage | None
        """
        if self.hasImage():
            return self._image.pixmap().toImage()
        return None

    def getCurrentLayerPixmapBeforeChangeTo(self, changeName):
        if self.currentLayer in self.layerHistory:
            history = self.layerHistory[self.currentLayer]
            i = len(history)
            while i > 0:
                entry = history[i - 1]
                if entry["note"] != changeName:
                    return entry["pixmap"]
                i -= 1
        return None

    def undoCurrentLayerLatestChange(self):
        if self.currentLayer in self.layerHistory:
            history = self.layerHistory[self.currentLayer]
            if len(history) > 1:
                previous = history[-2]
                latest = history[-1]

                if latest["type"] == "Tool" and latest["note"] == "Path Select":
                    # Undo path selection
                    if self.path:
                        self.path.clear()

                    for pathItem in self.selectPainterPaths:
                        if pathItem and pathItem in self.scene.items():
                            self.scene.removeItem(pathItem)

                    for pathPointItem in self.selectPainterPointPaths:
                        if pathPointItem and pathPointItem in self.scene.items():
                            self.scene.removeItem(pathPointItem)

                    if previous["note"] == "Path Select":
                        self.selectPoints, self.selectPainterPaths, self.selectPainterPointPaths = previous["value"]
                        if len(self.selectPoints) > 1:
                            self.buildPath(addToHistory=False)

                            # Remove the last entry from the history
                            self.layerHistory[self.currentLayer] = history[:-1]
                        else:
                            # Remove the last 2 entries from the history
                            self.layerHistory[self.currentLayer] = history[:-2]
                            self.selectPoints = []
                            self.selectPainterPaths = []
                            self.selectPainterPointPaths = []
                    else:
                        # Previous is not a path select
                        # Remove the last 2 entries from the history
                        self.layerHistory[self.currentLayer] = history[:-1]
                        self.selectPoints = []
                        self.selectPainterPaths = []
                        self.selectPainterPointPaths = []

                elif previous["type"] == "Slider":
                    if previous["value"]:
                        slider = getattr(self.parent, previous["object"])
                        slider.setValue(previous["value"])
                        setattr(self.parent, previous["object"], slider)

                        # Remove the last two entries
                        self.layerHistory[self.currentLayer] = history[:-2]
                        self.setImage(previous["pixmap"], True, previous["note"], previous["type"], previous["value"], previous["object"])
                        # Update GUI object value, e.g., slider setting
                
                        if len(self.layerHistory[self.currentLayer]) == 0:
                            self.layerHistory[self.currentLayer].append(previous)
                else:
                    # Generic undo
                    # Remove the last two entries
                    self.layerHistory[self.currentLayer] = history[:-2]
                    self.setImage(previous["pixmap"], True, previous["note"], previous["type"], previous["value"], previous["object"])
                    # Update GUI object value, e.g., slider setting
                
                    if len(self.layerHistory[self.currentLayer]) == 0:
                        self.layerHistory[self.currentLayer].append(previous)

    def getCurrentLayerLatestPixmap(self):
        if self.currentLayer in self.layerHistory:
            # Layer name checks out
            history = self.layerHistory[self.currentLayer]
            
            # History structure
            #
            # List of objects
            # {
            #    "note"   : "Crop",
            #    "pixmap" : QPixmap(...)
            #    "type"   : "Tool" or "Slider"
            #    "value"  : None or some value e.g., 10
            #    "object" : Relevant object, e.g., brightnessSlider <- will be used to update parent.brightnessSlider.setValue(...)
            # }

            if len(history) > 0:
                # Get most recent
                entry = history[-1]
                if "pixmap" in entry:
                    return entry["pixmap"]
        return None

    def getCurrentLayerPreviousPixmap(self):
        if self.currentLayer in self.layerHistory:
            # Layer name checks out
            history = self.layerHistory[self.currentLayer]
            
            # History structure
            #
            # List of objects
            # {
            #    "note"   : "Crop",
            #    "pixmap" : QPixmap(...)
            #    "type"   : "Tool" or "Slider"
            #    "value"  : None or some value e.g., 10
            #    "object" : Relevant object, e.g., brightnessSlider <- will be used to update parent.brightnessSlider.setValue(...)
            # }

            if len(history) > 1:
                # Get most recent
                entry = history[-2]
                if "pixmap" in entry:
                    return entry["pixmap"]
        return None

    def getCurrentLayerLatestPixmapBeforeSliderChange(self):
        if self.currentLayer in self.layerHistory:
            # Layer name checks out
            history = self.layerHistory[self.currentLayer]
            
            # History structure
            #
            # List of objects
            # {
            #    "note"   : "Crop",
            #    "pixmap" : QPixmap(...)
            #    "Type"   : "Tool" or "Slider"
            #    "value"  : None or some value e.g., 10
            #    "object" : Relevant object, e.g., brightnessSlider <- will be used to update parent.brightnessSlider.setValue(...)
            # }

            i = len(history)
            while i > 0:
                entry = history[i - 1]
                if "pixmap" in entry and entry["type"] != "Slider":
                    return entry["pixmap"]
                i -= 1

        return None

    def getCurrentLayerLatestPixmapBeforeLUTChange(self):
        if self.currentLayer in self.layerHistory:
            # Layer name checks out
            history = self.layerHistory[self.currentLayer]
            
            # History structure
            #
            # List of objects
            # {
            #    "note"   : "Crop",
            #    "pixmap" : QPixmap(...)
            #    "Type"   : "Tool" or "Slider"
            #    "value"  : None or some value e.g., 10
            #    "object" : Relevant object, e.g., brightnessSlider <- will be used to update parent.brightnessSlider.setValue(...)
            # }

            i = len(history)
            while i > 0:
                entry = history[i - 1]
                if "pixmap" in entry and entry["note"] != "LUT":
                    return entry["pixmap"]
                i -= 1

        return None

    def addToHistory(self, pixmap, explanationOfChange, typeOfChange, valueOfChange, objectOfChange):
        self.layerHistory[self.currentLayer].append({
            "note": explanationOfChange,
            "pixmap": pixmap,
            "type": typeOfChange,
            "value": valueOfChange,
            "object": objectOfChange
        })

    def duplicateCurrentLayer(self):
        if self.currentLayer in self.layerHistory:
            history = self.layerHistory[self.currentLayer]
            if len(history) > 0:
                latest = history[-1]

                # Create a new layer with latest as the starting point
                self.currentLayer = self.numLayersCreated
                self.numLayersCreated += 1
                self.layerHistory[self.currentLayer] = []
                self.addToHistory(latest["pixmap"], "Open", None, None, None)

    def setImage(self, image, addToHistory=True, explanationOfChange="", typeOfChange=None, valueOfChange=None, objectOfChange=None):
        """ Set the scene's current image pixmap to the input QImage or QPixmap.
        Raises a RuntimeError if the input image has type other than QImage or QPixmap.
        :type image: QImage | QPixmap
        """
        if type(image) is QPixmap:
            pixmap = image
        elif type(image) is QImage:
            pixmap = QPixmap.fromImage(image)
        # Add to layer history
        if addToHistory:
            if self.layerListDock:
                # Update the layer button pixmap to the new 
                self.layerListDock.setButtonPixmap(pixmap)
            self.addToHistory(pixmap.copy(), explanationOfChange, typeOfChange, valueOfChange, objectOfChange)
        
        ##########################################################################################
        # Grid for transparent images
        #########################################################################################

        # https://stackoverflow.com/a/67073067
        def checkerboard(w, h):
            from itertools import chain
            from math import ceil
            from PIL import Image

            m, n = (int(w / 100), int(h / 100))             # Checker dimension (x, y)

            if m < 100:
                if m == 0:
                    m = 1
                m *= 100/m
                m = int(m)
                n = int(m * h / w)
            elif n < 100:
                if n == 0:
                    n = 1
                n *= 100/n 
                n = int(n)
                m = int(n * w / h)

            c1 = (225, 255, 255, 0)                  # First color
            c2 = (83, 83, 83)                        # Second color
            mode = 'L' if isinstance(c1, int) else 'RGBA'   # Mode from first color

            # Generate pixel-wise checker, even x dimension
            if m % 2 == 0:
                pixels = [[c1, c2] for i in range(int(m/2))] + \
                         [[c2, c1] for i in range(int(m/2))]
                pixels = [list(chain(*pixels)) for i in range(ceil(n/2))]

            # Generate pixel-wise checker, odd x dimension
            else:
                pixels = [[c1, c2] for i in range(ceil(m*n/2))]

            # Generate final Pillow-compatible pixel values
            pixels = list(chain(*pixels))[:(m*n)]

            # Generate Pillow image from pixel values, resize to final image size, and save
            checker = Image.new(mode, (m, n))
            checker.putdata(pixels)
            checker = checker.resize((w, h), Image.NEAREST)
            return checker

        original = pixmap.copy()

        width = pixmap.width()
        height = pixmap.height()

        if not self.checkerBoard:
            self.checkerBoard = checkerboard(width, height)
            self.checkerBoard = self.ImageToQPixmap(self.checkerBoard)
        else:
            if self.checkerBoardHeight != height or self.checkerBoardWidth != width:
                self.checkerBoard = checkerboard(width, height)
                self.checkerBoard = self.ImageToQPixmap(self.checkerBoard)
        if self.checkerBoard:
            painter = QPainter(pixmap)
            painter.drawPixmap(QPoint(), self.checkerBoard)
            painter.drawPixmap(QPoint(), original)
            painter.end()

        #########################################################################################
        
        if self.hasImage():
            self._image.setPixmap(pixmap)
        else:
            self._image = self.scene.addPixmap(pixmap)

        # Better quality pixmap scaling?
        # !!! This will distort actual pixel data when zoomed way in.
        #     For scientific image analysis, you probably don't want this.
        # self._pixmap.setTransformationMode(Qt.SmoothTransformation)

        self.setSceneRect(QRectF(pixmap.rect()))  # Set scene size to image size.
        self.updateViewer()
        if getattr(self.parent, "UpdateHistogramPlot", None):
            self.parent.UpdateHistogramPlot()

    
    def open(self, filepath=None):
        """ Load an image from file.
        Without any arguments, loadImageFromFile() will pop up a file dialog to choose the image file.
        With a fileName argument, loadImageFromFile(fileName) will attempt to load the specified image file directly.
        """
        if filepath is None:
            filepath, dummy = QFileDialog.getOpenFileName(self, "Open image file.")
        if len(filepath) and os.path.isfile(filepath):
            self._current_filename = filepath
            image = QImage(filepath)
            self.setImage(image, True, "Open")

    def save(self, filepath=None):
        path = self._current_filename
        if filepath:
            path = filepath
            self._current_filename = path

        self.pixmap().save(path, None, 100)

    def updateViewer(self):
        """ Show current zoom (if showing entire image, apply current aspect ratio mode).
        """
        if not self.hasImage():
            return
        if len(self.zoomStack):
            self.fitInView(self.zoomStack[-1], self.aspectRatioMode)  # Show zoomed rect.
        else:
            self.fitInView(self.sceneRect(), self.aspectRatioMode)  # Show entire image.

    def clearZoom(self):
        if len(self.zoomStack) > 0:
            self.zoomStack = []
            self.updateViewer()
            self.viewChanged.emit()

    def resizeEvent(self, event):
        """ Maintain current zoom on resize.
        """
        self.updateViewer()

    def QPixmapToImage(self, pixmap):
        width = pixmap.width()
        height = pixmap.height()
        image = pixmap.toImage()

        byteCount = image.bytesPerLine() * height
        data = image.constBits().asstring(byteCount)
        return Image.frombuffer('RGBA', (width, height), data, 'raw', 'BGRA', 0, 1)

    def QImageToImage(self, qimage):
        width = qimage.width()
        height = qimage.height()
        image = qimage

        byteCount = image.bytesPerLine() * height
        data = image.constBits().asstring(byteCount)
        return Image.frombuffer('RGBA', (width, height), data, 'raw', 'BGRA', 0, 1)

    def ImageToQPixmap(self, image):
        return QPixmap.fromImage(ImageQt(image))

    def mousePressEvent(self, event):
        """ Start mouse pan or zoom mode.
        """
        # Ignore dummy events. e.g., Faking pan with left button ScrollHandDrag.
        dummyModifiers = Qt.KeyboardModifier(Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier
                                             | Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.MetaModifier)
        if event.modifiers() == dummyModifiers:
            QGraphicsView.mousePressEvent(self, event)
            event.accept()
            return

        if event.button() == self.regionZoomButton:
            self._isLeftMouseButtonPressed = True

        # # Draw ROI
        # if self.drawROI is not None:
        #     if self.drawROI == "Ellipse":
        #         # Click and drag to draw ellipse. +Shift for circle.
        #         pass
        #     elif self.drawROI == "Rect":
        #         # Click and drag to draw rectangle. +Shift for square.
        #         pass
        #     elif self.drawROI == "Line":
        #         # Click and drag to draw line.
        #         pass
        #     elif self.drawROI == "Polygon":
        #         # Click to add points to polygon. Double-click to close polygon.
        #         pass

        if self._isColorPicking:
            self.performColorPick(event)
        elif self._isPainting:
            if (self.regionZoomButton is not None) and (event.button() == self.regionZoomButton):
                self.performPaint(event)
        elif self._isErasing:
            if (self.regionZoomButton is not None) and (event.button() == self.regionZoomButton):
                self.performErase(event)
        elif self._isFilling:
            if (self.regionZoomButton is not None) and (event.button() == self.regionZoomButton):
                self.performFill(event)
        elif self._isSelectingRect:
            if not self._isSelectingRectStarted:
                # Start dragging a region crop box?
                if (self.regionZoomButton is not None) and (event.button() == self.regionZoomButton):
                    self._isSelectingRectStarted = True
                    
                    self._pixelPosition = event.pos()  # store pixel position
                    self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
                    QGraphicsView.mousePressEvent(self, event)
                    event.accept()
                    return
            else:
                event.ignore()
        elif self._isSelectingPath:
            # TODO: https://stackoverflow.com/questions/63568214/qpainter-delete-previously-drawn-shapes
            #
            #
            # Start dragging a region crop box?
            if (self.regionZoomButton is not None) and (event.button() == self.regionZoomButton):
                self._pixelPosition = event.pos()  # store pixel position
                self.selectPoints.append(QPointF(self.mapToScene(event.pos())))
                QGraphicsView.mousePressEvent(self, event)
                self.buildPath()
                event.accept()
                return
        elif self._isRemovingSpots:
            if (self.regionZoomButton is not None) and (event.button() == self.regionZoomButton):
                if not self._targetSelected:
                    # Target selected

                    # Save the target position
                    self._targetPos = self.mapToScene(event.pos())
                    self._targetPos = (int(self._targetPos.x()), int(self._targetPos.y()))
                    # Set toggle
                    self._targetSelected = True
                    self.showSpotRemovalResultAtMousePosition(event)
                else:
                    self.removeSpots(event)
        elif self._isBlurring:
            if (self.regionZoomButton is not None) and (event.button() == self.regionZoomButton):
                self.blur(event)
        else:
            # Zoom
            # Start dragging a region zoom box?
            if (self.regionZoomButton is not None) and (event.button() == self.regionZoomButton):
                self._pixelPosition = event.pos()  # store pixel position
                self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
                QGraphicsView.mousePressEvent(self, event)
                event.accept()
                self._isZooming = True
                return

            if (self.zoomOutButton is not None) and (event.button() == self.zoomOutButton):
                if len(self.zoomStack):
                    self.zoomStack.pop()
                    self.updateViewer()
                    self.viewChanged.emit()
                event.accept()
                return

        # Start dragging to pan?
        if (self.panButton is not None) and (event.button() == self.panButton):
            self._pixelPosition = event.pos()  # store pixel position
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            if self.panButton == Qt.MouseButton.LeftButton:
                QGraphicsView.mousePressEvent(self, event)
            else:
                # ScrollHandDrag ONLY works with LeftButton, so fake it.
                # Use a bunch of dummy modifiers to notify that event should NOT be handled as usual.
                self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
                dummyModifiers = Qt.KeyboardModifier(Qt.KeyboardModifier.ShiftModifier
                                                     | Qt.KeyboardModifier.ControlModifier
                                                     | Qt.KeyboardModifier.AltModifier
                                                     | Qt.KeyboardModifier.MetaModifier)
                dummyEvent = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(event.pos()), Qt.MouseButton.LeftButton,
                                         event.buttons(), dummyModifiers)
                self.mousePressEvent(dummyEvent)
            sceneViewport = self.mapToScene(self.viewport().rect()).boundingRect().intersected(self.sceneRect())
            self._scenePosition = sceneViewport.topLeft()
            event.accept()
            self._isPanning = True
            return

        scenePos = self.mapToScene(event.pos())
        if event.button() == Qt.MouseButton.LeftButton:
            self.leftMouseButtonPressed.emit(scenePos.x(), scenePos.y())
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.middleMouseButtonPressed.emit(scenePos.x(), scenePos.y())
        elif event.button() == Qt.MouseButton.RightButton:
            self.rightMouseButtonPressed.emit(scenePos.x(), scenePos.y())

        QGraphicsView.mousePressEvent(self, event)

    def mouseReleaseEvent(self, event):
        """ Stop mouse pan or zoom mode (apply zoom if valid).
        """
        # Ignore dummy events. e.g., Faking pan with left button ScrollHandDrag.
        dummyModifiers = Qt.KeyboardModifier(Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier
                                             | Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.MetaModifier)
        if event.modifiers() == dummyModifiers:
            QGraphicsView.mouseReleaseEvent(self, event)
            event.accept()
            return

        if event.button() == self.regionZoomButton:
            self._isLeftMouseButtonPressed = False

        if self._isSelectingRect:
            if self._isSelectingRectStarted:
                # Finish dragging a region crop box?
                if (self.regionZoomButton is not None) and (event.button() == self.regionZoomButton):
                    QGraphicsView.mouseReleaseEvent(self, event)
                    self._selectRect = self.scene.selectionArea().boundingRect().intersected(self.sceneRect())
                    # Clear current selection area (i.e. rubberband rect).
                    self.scene.setSelectionArea(QPainterPath())
                    self.setDragMode(QGraphicsView.DragMode.NoDrag)
                    # If zoom box is 3x3 screen pixels or smaller, do not zoom and proceed to process as a click release.
                    zoomPixelWidth = abs(event.pos().x() - self._pixelPosition.x())
                    zoomPixelHeight = abs(event.pos().y() - self._pixelPosition.y())
                    if zoomPixelWidth > 3 and zoomPixelHeight > 3:
                        if self._selectRect.isValid() and (self._selectRect != self.sceneRect()):
                            # Create a new crop item using user-drawn rectangle
                            pixmap = self.getCurrentLayerLatestPixmap()
                            if self._selectRectItem:
                                self._selectRectItem.setRect(self._selectRect)
        else:
            # Finish dragging a region zoom box?
            if (self.regionZoomButton is not None) and (event.button() == self.regionZoomButton):
                QGraphicsView.mouseReleaseEvent(self, event)
                zoomRect = self.scene.selectionArea().boundingRect().intersected(self.sceneRect())
                # Clear current selection area (i.e. rubberband rect).
                self.scene.setSelectionArea(QPainterPath())
                self.setDragMode(QGraphicsView.DragMode.NoDrag)
                # If zoom box is 3x3 screen pixels or smaller, do not zoom and proceed to process as a click release.
                zoomPixelWidth = abs(event.pos().x() - self._pixelPosition.x())
                zoomPixelHeight = abs(event.pos().y() - self._pixelPosition.y())
                if zoomPixelWidth > 3 and zoomPixelHeight > 3:
                    if zoomRect.isValid() and (zoomRect != self.sceneRect()):
                        self.zoomStack.append(zoomRect)
                        self.updateViewer()
                        self.viewChanged.emit()
                        event.accept()
                        self._isZooming = False
                        return

        # Finish panning?
        if (self.panButton is not None) and (event.button() == self.panButton):
            if self.panButton == Qt.MouseButton.LeftButton:
                QGraphicsView.mouseReleaseEvent(self, event)
            else:
                # ScrollHandDrag ONLY works with LeftButton, so fake it.
                # Use a bunch of dummy modifiers to notify that event should NOT be handled as usual.
                self.viewport().setCursor(Qt.CursorShape.ArrowCursor)
                dummyModifiers = Qt.KeyboardModifier(Qt.KeyboardModifier.ShiftModifier
                                                     | Qt.KeyboardModifier.ControlModifier
                                                     | Qt.KeyboardModifier.AltModifier
                                                     | Qt.KeyboardModifier.MetaModifier)
                dummyEvent = QMouseEvent(QEvent.Type.MouseButtonRelease, QPointF(event.pos()),
                                         Qt.MouseButton.LeftButton, event.buttons(), dummyModifiers)
                self.mouseReleaseEvent(dummyEvent)
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            if len(self.zoomStack) > 0:
                sceneViewport = self.mapToScene(self.viewport().rect()).boundingRect().intersected(self.sceneRect())
                delta = sceneViewport.topLeft() - self._scenePosition
                self.zoomStack[-1].translate(delta)
                self.zoomStack[-1] = self.zoomStack[-1].intersected(self.sceneRect())
                self.viewChanged.emit()
            event.accept()
            self._isPanning = False
            return

        scenePos = self.mapToScene(event.pos())
        if event.button() == Qt.MouseButton.LeftButton:
            self.leftMouseButtonReleased.emit(scenePos.x(), scenePos.y())
        elif event.button() == Qt.MouseButton.MiddleButton:
            self.middleMouseButtonReleased.emit(scenePos.x(), scenePos.y())
        elif event.button() == Qt.MouseButton.RightButton:
            self.rightMouseButtonReleased.emit(scenePos.x(), scenePos.y())

        QGraphicsView.mouseReleaseEvent(self, event)

    def mouseDoubleClickEvent(self, event):
        """ Show entire image.
        """
        # Zoom out on double click?
        if (self.zoomOutButton is not None) and (event.button() == self.zoomOutButton):
            self.clearZoom()
            event.accept()
            return

        scenePos = self.mapToScene(event.pos())
        if event.button() == Qt.MouseButton.LeftButton:
            self.leftMouseButtonDoubleClicked.emit(scenePos.x(), scenePos.y())
        elif event.button() == Qt.MouseButton.RightButton:
            self.rightMouseButtonDoubleClicked.emit(scenePos.x(), scenePos.y())

        QGraphicsView.mouseDoubleClickEvent(self, event)

    def wheelEvent(self, event):
        if self.wheelZoomFactor is not None:
            if self.wheelZoomFactor == 1:
                return
            if event.angleDelta().y() < 0:
                # zoom in
                if len(self.zoomStack) == 0:
                    self.zoomStack.append(self.sceneRect())
                elif len(self.zoomStack) > 1:
                    del self.zoomStack[:-1]
                zoomRect = self.zoomStack[-1]
                center = zoomRect.center()
                zoomRect.setWidth(zoomRect.width() / self.wheelZoomFactor)
                zoomRect.setHeight(zoomRect.height() / self.wheelZoomFactor)
                zoomRect.moveCenter(center)
                self.zoomStack[-1] = zoomRect.intersected(self.sceneRect())
                self.updateViewer()
                self.viewChanged.emit()
                self.zoomLevel += 1
            else:
                # zoom out
                if len(self.zoomStack) == 0:
                    # Already fully zoomed out.
                    return
                if len(self.zoomStack) > 1:
                    del self.zoomStack[:-1]
                zoomRect = self.zoomStack[-1]
                center = zoomRect.center()
                zoomRect.setWidth(zoomRect.width() * self.wheelZoomFactor)
                zoomRect.setHeight(zoomRect.height() * self.wheelZoomFactor)
                zoomRect.moveCenter(center)
                self.zoomStack[-1] = zoomRect.intersected(self.sceneRect())
                if self.zoomStack[-1] == self.sceneRect():
                    self.zoomStack = []
                self.updateViewer()
                self.viewChanged.emit()
                self.zoomLevel -= 1
            event.accept()
            return

        QGraphicsView.wheelEvent(self, event)

    def enterEvent(self, event):
        self.setCursor(Qt.CursorShape.CrossCursor)

    def leaveEvent(self, event):
        self.setCursor(Qt.CursorShape.ArrowCursor)

    def Luminance(self, pixel):
        return (0.299 * pixel[0] + 0.587 * pixel[1] + 0.114 * pixel[2])

    def isSimilar(self, pixel_a, pixel_b, threshold):
        return abs(self.Luminance(pixel_a) - self.Luminance(pixel_b)) < threshold
