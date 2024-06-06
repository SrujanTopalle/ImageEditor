from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QSlider,
    QToolButton,
    QFileDialog,
    QStatusBar
)
from PyQt6.QtGui import QPixmap
import sys

from QImageViewer import QtImageViewer
from PyQt6.QtGui import QKeySequence
import pyqtgraph as pg
import os
from QFlowLayout import QFlowLayout
from PIL import Image, ImageEnhance, ImageFilter
import QCurveWidget

class Gui(QtWidgets.QMainWindow):

    sliderChangeSignal = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(Gui, self).__init__(parent)
        self.setWindowTitle('Image Editor Tool')
        self.setMinimumHeight(850)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        ##############################################################################################
        ##############################################################################################
        # Create Histogram
        ##############################################################################################
        ##############################################################################################

        # Compute image histogram
        r_histogram = []
        g_histogram = []
        b_histogram = []
        
        # ITU-R 601-2 luma transform:
        luma_histogram = []

        # Create histogram plot
        self.ImageHistogramPlot = pg.plot()
        x = list(range(len(r_histogram)))
        self.ImageHistogramGraphRed = pg.PlotCurveItem(x = x, y = r_histogram, fillLevel=2, width = 1.0, brush=(255,0,0,80))
        self.ImageHistogramGraphGreen = pg.PlotCurveItem(x = x, y = g_histogram, fillLevel=2, width = 1.0, brush=(0,255,0,80))
        self.ImageHistogramGraphBlue = pg.PlotCurveItem(x = x, y = b_histogram, fillLevel=2, width = 1.0, brush=(0,0,255,80))
        self.ImageHistogramGraphLuma = pg.PlotCurveItem(x = x, y = luma_histogram, fillLevel=2, width = 1.0, brush=(255,255,255,80))
        self.ImageHistogramPlot.addItem(self.ImageHistogramGraphRed)
        self.ImageHistogramPlot.addItem(self.ImageHistogramGraphGreen)
        self.ImageHistogramPlot.addItem(self.ImageHistogramGraphBlue)
        self.ImageHistogramPlot.addItem(self.ImageHistogramGraphLuma)
        self.HistogramContent = None
        self.ImageHistogramPlot.hide()

        
        ##############################################################################################
        ##############################################################################################
        # Adjustment Sliders
        ##############################################################################################
        ##############################################################################################

        # State of enhance sliders
        self.RedFactor = 100
        self.GreenFactor = 100
        self.BlueFactor = 100
        self.Color = 100
        self.Brightness = 100
        self.Contrast = 100
        self.Sharpness = 100

        # State of filter sliders
        self.GaussianBlurRadius = 0

        self.timer_id = -1
        self.sliderExplanationOfChange = None
        self.sliderTypeOfChange = None
        self.sliderValueOfChange = None
        self.sliderObjectOfChange = None

        ##############################################################################################
        ##############################################################################################
        # Keyboard Shortcuts
        ##############################################################################################
        ##############################################################################################

        self.OpenShortcut = QtGui.QShortcut(QKeySequence("Ctrl+O"), self)
        self.OpenShortcut.activated.connect(self.OnOpen)

        self.SaveShortcut = QtGui.QShortcut(QKeySequence("Ctrl+S"), self)
        self.SaveShortcut.activated.connect(self.OnSaveAs)

        self.SaveAsShortcut = QtGui.QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        self.SaveAsShortcut.activated.connect(self.OnSaveAs)

        self.UndoShortcut = QtGui.QShortcut(QKeySequence("Ctrl+Z"), self)
        self.UndoShortcut.activated.connect(self.OnUndo)


        
        ##############################################################################################
        ##############################################################################################
        # Rotate Tool
        ##############################################################################################
        ##############################################################################################

        self.RotateToolButton = QToolButton(self)
        self.RotateToolButton.setText("&Rotate")
        self.setIconPixmapWithColor(self.RotateToolButton, "icons/rotate_left.svg")
        self.RotateToolButton.setToolTip("Rotate")
        self.RotateToolButton.setCheckable(True)
        self.RotateToolButton.toggled.connect(self.OnRotateToolButton)

        ##############################################################################################
        ##############################################################################################
        # Flip Left Right Tool
        ##############################################################################################
        ##############################################################################################

        self.FlipLeftRightToolButton = QToolButton(self)
        self.FlipLeftRightToolButton.setText("&Flip Left-Right")
        self.setIconPixmapWithColor(self.FlipLeftRightToolButton, "icons/flip_left_right.svg")
        self.FlipLeftRightToolButton.setToolTip("Flip Left-Right")
        self.FlipLeftRightToolButton.setCheckable(True)
        self.FlipLeftRightToolButton.toggled.connect(self.OnFlipLeftRightToolButton)

        ##############################################################################################
        ##############################################################################################
        # Flip Top Bottom Tool
        ##############################################################################################
        ##############################################################################################

        self.FlipTopBottomToolButton = QToolButton(self)
        self.FlipTopBottomToolButton.setText("&Flip Top-Bottom")
        self.setIconPixmapWithColor(self.FlipTopBottomToolButton, "icons/flip_top_bottom.svg")
        self.FlipTopBottomToolButton.setToolTip("Flip Top-Bottom")
        self.FlipTopBottomToolButton.setCheckable(True)
        self.FlipTopBottomToolButton.toggled.connect(self.OnFlipTopBottomToolButton)

       
        
        ##############################################################################################
        ##############################################################################################
        # White Balance Tool
        # https://github.com/mahmoudnafifi/WB_sRGB
        ##############################################################################################
        ##############################################################################################

        self.WhiteBalanceToolButton = QToolButton(self)
        self.WhiteBalanceToolButton.setText("& AI White Balance")
        self.WhiteBalanceToolButton.setToolTip("AI White Balance")
        self.setIconPixmapWithColor(self.WhiteBalanceToolButton, "icons/white_balance.svg")
        self.WhiteBalanceToolButton.setCheckable(True)
        self.WhiteBalanceToolButton.toggled.connect(self.OnWhiteBalanceToolButton)

        ##############################################################################################
        ##############################################################################################
        # Sliders Tool
        ##############################################################################################
        ##############################################################################################

        self.SlidersToolButton = QToolButton(self)
        self.SlidersToolButton.setText("&Sliders")
        self.SlidersToolButton.setToolTip("Sliders")
        self.setIconPixmapWithColor(self.SlidersToolButton, "icons/sliders.svg")
        self.SlidersToolButton.setCheckable(True)
        self.SlidersToolButton.toggled.connect(self.OnSlidersToolButton)

        ##############################################################################################
        ##############################################################################################
        # Curve Editor Tool
        ##############################################################################################
        ##############################################################################################

        self.CurveEditorToolButton = QToolButton(self)
        self.CurveEditorToolButton.setText("&Curves")
        self.CurveEditorToolButton.setToolTip("Curves")
        self.setIconPixmapWithColor(self.CurveEditorToolButton, "icons/curve.svg")
        self.CurveEditorToolButton.setCheckable(True)
        self.CurveEditorToolButton.toggled.connect(self.OnCurveEditorToolButton)

        ##############################################################################################
        ##############################################################################################
        # Instagram Filters Tool
        ##############################################################################################
        ##############################################################################################

        self.InstagramFiltersToolButton = QToolButton(self)
        self.InstagramFiltersToolButton.setText("&Filters")
        self.InstagramFiltersToolButton.setToolTip("Filters")
        self.setIconPixmapWithColor(self.InstagramFiltersToolButton, "icons/instagram.svg")
        self.InstagramFiltersToolButton.setCheckable(True)
        self.InstagramFiltersToolButton.toggled.connect(self.OnInstagramFiltersToolButton)

        ##############################################################################################
        ##############################################################################################
        # Histogram Viewer Tool
        ##############################################################################################
        ##############################################################################################

        self.HistogramToolButton = QToolButton(self)
        self.HistogramToolButton.setText("&Histogram")
        self.HistogramToolButton.setToolTip("Histogram")
        self.setIconPixmapWithColor(self.HistogramToolButton, "icons/histogram.svg")
        self.HistogramToolButton.setCheckable(True)
        self.HistogramToolButton.toggled.connect(self.OnHistogramToolButton)

        ##############################################################################################
        ##############################################################################################
        # Toolbar
        ##############################################################################################
        ##############################################################################################

        self.tools = {
                       
            "histogram": {
                "tool": "HistogramToolButton",
                "var": '_isShowingHistogram'
            },
            
              
            "instagram_filters": {
                "tool": "InstagramFiltersToolButton",
                "var": '_isApplyingFilter'
            },
        }

        self.ToolbarDockWidget = QtWidgets.QDockWidget("Tools")
        self.ToolbarDockWidget.setTitleBarWidget(QtWidgets.QWidget())
        ToolbarContent = QtWidgets.QWidget()
        ToolbarLayout = QFlowLayout(ToolbarContent)
        ToolbarLayout.setSpacing(0)

        self.ToolButtons = [
            self.SlidersToolButton, self.HistogramToolButton, self.CurveEditorToolButton, 
            
            self.RotateToolButton,
            self.FlipLeftRightToolButton, self.FlipTopBottomToolButton,
           
            self.InstagramFiltersToolButton,
            self.WhiteBalanceToolButton,  
        ]

        for button in self.ToolButtons:
            button.setIconSize(QtCore.QSize(20, 20))
            button.setEnabled(False)
            button.setCursor(QtGui.QCursor(QtCore.Qt.CursorShape.ArrowCursor))
            ToolbarLayout.addWidget(button)

        ToolbarContent.setLayout(ToolbarLayout)
        self.ToolbarDockWidget.setWidget(ToolbarContent)

        ##############################################################################################
        ##############################################################################################
        # Left Dock
        ##############################################################################################
        ##############################################################################################

        self.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea, self.ToolbarDockWidget)
        self.ToolbarDockWidget.setFloating(True)
        self.ToolbarDockWidget.setGeometry(QtCore.QRect(1550, 250, 100, 400))

        ##############################################################################################
        ##############################################################################################
        # Show Window
        ##############################################################################################
        ##############################################################################################

        self.initImageViewer()
        self.showMaximized()

        self.threadpool = QtCore.QThreadPool()
        self.sliderChangedPixmap = None
        self.sliderExplanationOfChange = None
        self.sliderTypeOfChange = None
        self.sliderValueOfChange = None
        self.sliderObjectOfChange = None
        self.sliderChangeSignal.connect(self.onUpdateImageCompleted)
        self.sliderWorkers = []

        self.resizeDockWidgets()

    def setIconPixmapWithColor(self, button, filename, findColor='black', newColor='white'):
        pixmap = QPixmap(filename)
        mask = pixmap.createMaskFromColor(QtGui.QColor(findColor), Qt.MaskMode.MaskOutColor)
        pixmap.fill((QtGui.QColor(newColor)))
        pixmap.setMask(mask)
        button.setIcon(QtGui.QIcon(pixmap))

    def setToolButtonStyleChecked(self, button):
        button.setStyleSheet('''
            border-color: rgb(22, 22, 22);
            background-color: rgb(90, 90, 90);
            border-style: solid;
        ''')

    def setToolButtonStyleUnchecked(self, button):
        button.setStyleSheet("")

    def resizeDockWidgets(self):
        pass
        # self.resizeDocks([self.ToolbarDockWidget], [200], Qt.Orientation.Vertical)

    @QtCore.pyqtSlot(int, str)
    def updateProgressBar(self, e, label):
        self.progressBar.setValue(e)
        self.progressBarLabel.setText(label)

    def initImageViewer(self):
        self.image_viewer = QtImageViewer(self)
        self.CurvesDock = None

        # Set viewer's aspect ratio mode.
        # !!! ONLY applies to full image view.
        # !!! Aspect ratio always ignored when zoomed.
        #   Qt.AspectRatioMode.IgnoreAspectRatio: Fit to viewport.
        #   Qt.AspectRatioMode.KeepAspectRatio: Fit in viewport using aspect ratio.
        #   Qt.AspectRatioMode.KeepAspectRatioByExpanding: Fill viewport using aspect ratio.
        self.image_viewer.aspectRatioMode = Qt.AspectRatioMode.KeepAspectRatio
    
        # Set the viewer's scroll bar behaviour.
        #   Qt.ScrollBarPolicy.ScrollBarAlwaysOff: Never show scroll bar.
        #   Qt.ScrollBarPolicy.ScrollBarAlwaysOn: Always show scroll bar.
        #   Qt.ScrollBarPolicy.ScrollBarAsNeeded: Show scroll bar only when zoomed.
        self.image_viewer.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.image_viewer.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    
        # Allow zooming by draggin a zoom box with the left mouse button.
        # !!! This will still emit a leftMouseButtonReleased signal if no dragging occured,
        #     so you can still handle left mouse button clicks in this way.
        #     If you absolutely need to handle a left click upon press, then
        #     either disable region zooming or set it to the middle or right button.
        self.image_viewer.regionZoomButton = Qt.MouseButton.LeftButton  # set to None to disable
    
        # Pop end of zoom stack (double click clears zoom stack).
        self.image_viewer.zoomOutButton = Qt.MouseButton.RightButton  # set to None to disable
    
        # Mouse wheel zooming.
        self.image_viewer.wheelZoomFactor = 1.25  # Set to None or 1 to disable
    
        # Allow panning with the middle mouse button.
        self.image_viewer.panButton = Qt.MouseButton.MiddleButton  # set to None to disable

        # Set the central widget of the Window. Widget will expand
        # to take up all the space in the window by default.
        self.setCentralWidget(self.image_viewer)

    def resetSliderValues(self):
        # State of enhance sliders
        self.RedFactor = 100
        self.BlueFactor = 100
        self.GreenFactor = 100
        self.Color = 100
        self.Brightness = 100
        self.Contrast = 100
        self.Sharpness = 100
        self.GaussianBlurRadius = 0

        self.RedColorSlider.setValue(self.RedFactor)        
        self.GreenColorSlider.setValue(self.GreenFactor)        
        self.BlueColorSlider.setValue(self.BlueFactor) 
        self.ColorSlider.setValue(self.Color)        
        self.BrightnessSlider.setValue(self.Brightness)
        self.ContrastSlider.setValue(self.Contrast)
        self.SharpnessSlider.setValue(self.Sharpness)
        self.GaussianBlurSlider.setValue(self.GaussianBlurRadius)

    def getCurrentLayerLatestPixmap(self):
        return self.image_viewer.getCurrentLayerLatestPixmap()

    def processSliderChange(self, explanationOfChange, typeOfChange, valueOfChange, objectOfChange):
        self.sliderExplanationOfChange = explanationOfChange
        self.sliderTypeOfChange = typeOfChange
        self.sliderValueOfChange = valueOfChange
        self.sliderObjectOfChange = objectOfChange

        if self.timer_id != -1:
            self.killTimer(self.timer_id)

        self.timer_id = self.startTimer(500)

    def QPixmapToImage(self, pixmap):
        width = pixmap.width()
        height = pixmap.height()
        image = pixmap.toImage()

        byteCount = image.bytesPerLine() * height
        data = image.constBits().asstring(byteCount)
        return Image.frombuffer('RGBA', (width, height), data, 'raw', 'BGRA', 0, 1)

    def ImageToQPixmap(self, image):
        from PIL.ImageQt import ImageQt
        return QPixmap.fromImage(ImageQt(image))

    def EnhanceImage(self, Pixmap, Property, value):
        CurrentImage = self.QPixmapToImage(Pixmap)
        AdjustedImage = Property(CurrentImage).enhance(float(value) / 100)
        return self.ImageToQPixmap(AdjustedImage)

    def ApplyGaussianBlur(self, Pixmap, value):
        CurrentImage = self.QPixmapToImage(Pixmap)
        AdjustedImage = CurrentImage.filter(ImageFilter.GaussianBlur(radius=value))
        return self.ImageToQPixmap(AdjustedImage)

    def UpdateReds(self, Pixmap, value):
        CurrentImage = self.QPixmapToImage(Pixmap)

        # Split into channels
        r, g, b, a = CurrentImage.split()

        # Increase Reds
        r = r.point(lambda i: i * value)

        # Recombine back to RGB image
        AdjustedImage = Image.merge('RGBA', (r, g, b, a))

        return self.ImageToQPixmap(AdjustedImage)

    def AddRedColorSlider(self, layout):
        self.RedColorSlider = QSlider(QtCore.Qt.Orientation.Horizontal)
        self.RedColorSlider.setRange(0, 200) # 1 is original image, 0 is black image
        layout.addRow("Red", self.RedColorSlider)

        # Default value of the Color slider
        self.RedColorSlider.setValue(100) 

        self.RedColorSlider.valueChanged.connect(self.OnRedColorChanged)

    def OnRedColorChanged(self, value):
        self.RedFactor = value
        self.processSliderChange("Red", "Slider", value, "RedColorSlider")

    def UpdateGreens(self, Pixmap, value):
        CurrentImage = self.QPixmapToImage(Pixmap)

        # Split into channels
        r, g, b, a = CurrentImage.split()

        # Increase Greens
        g = g.point(lambda i: i * value)

        # Recombine back to RGB image
        AdjustedImage = Image.merge('RGBA', (r, g, b, a))

        return self.ImageToQPixmap(AdjustedImage)

    def AddGreenColorSlider(self, layout):
        self.GreenColorSlider = QSlider(QtCore.Qt.Orientation.Horizontal)
        self.GreenColorSlider.setRange(0, 200) # 1 is original image, 0 is black image
        layout.addRow("Green", self.GreenColorSlider)

        # Default value of the Color slider
        self.GreenColorSlider.setValue(100) 

        self.GreenColorSlider.valueChanged.connect(self.OnGreenColorChanged)

    def OnGreenColorChanged(self, value):
        self.GreenFactor = value
        self.processSliderChange("Green", "Slider", value, "GreenColorSlider")

    def UpdateBlues(self, Pixmap, value):
        CurrentImage = self.QPixmapToImage(Pixmap)

        # Split into channels
        r, g, b, a = CurrentImage.split()

        # Increase Blues
        b = b.point(lambda i: i * value)

        # Recombine back to RGB image
        AdjustedImage = Image.merge('RGBA', (r, g, b, a))

        return self.ImageToQPixmap(AdjustedImage)

    def AddBlueColorSlider(self, layout):
        self.BlueColorSlider = QSlider(QtCore.Qt.Orientation.Horizontal)
        self.BlueColorSlider.setRange(0, 200) # 1 is original image, 0 is black image
        layout.addRow("Blue", self.BlueColorSlider)

        # Default value of the Color slider
        self.BlueColorSlider.setValue(100) 

        self.BlueColorSlider.valueChanged.connect(self.OnBlueColorChanged)

    def OnBlueColorChanged(self, value):
        self.BlueFactor = value
        self.processSliderChange("Blue", "Slider", value, "BlueColorSlider")

    def AddColorSlider(self, layout):
        self.ColorSlider = QSlider(QtCore.Qt.Orientation.Horizontal)
        self.ColorSlider.setRange(0, 200) # 1 is original image, 0 is black image
        layout.addRow("Saturation", self.ColorSlider)

        # Default value of the Color slider
        self.ColorSlider.setValue(100) 

        self.ColorSlider.valueChanged.connect(self.OnColorChanged)

    def OnColorChanged(self, value):
        self.Color = value
        self.processSliderChange("Saturation", "Slider", value, "ColorSlider")

    def AddBrightnessSlider(self, layout):
        self.BrightnessSlider = QSlider(QtCore.Qt.Orientation.Horizontal)
        self.BrightnessSlider.setRange(0, 200) # 1 is original image, 0 is black image
        layout.addRow("Brightness", self.BrightnessSlider)

        # Default value of the brightness slider
        self.BrightnessSlider.setValue(100) 

        self.BrightnessSlider.valueChanged.connect(self.OnBrightnessChanged)

    def OnBrightnessChanged(self, value):
        self.Brightness = value
        self.processSliderChange("Brightness", "Slider", value, "BrightnessSlider")

    def AddContrastSlider(self, layout):
        self.ContrastSlider = QSlider(QtCore.Qt.Orientation.Horizontal)
        self.ContrastSlider.setRange(0, 200) # 1 is original image, 0 is a solid grey image
        layout.addRow("Contrast", self.ContrastSlider)

        # Default value of the brightness slider
        self.ContrastSlider.setValue(100) 

        self.ContrastSlider.valueChanged.connect(self.OnContrastChanged)

    def OnContrastChanged(self, value):
        self.Contrast = value
        self.processSliderChange("Contrast", "Slider", value, "ContrastSlider")

    def AddSharpnessSlider(self, layout):
        self.SharpnessSlider = QSlider(QtCore.Qt.Orientation.Horizontal)
        self.SharpnessSlider.setRange(0, 200) # 1 is original image, 0 is black image
        layout.addRow("Sharpness", self.SharpnessSlider)

        # Default value of the Sharpness slider
        self.SharpnessSlider.setValue(100) 

        self.SharpnessSlider.valueChanged.connect(self.OnSharpnessChanged)

    def OnSharpnessChanged(self, value):
        self.Sharpness = value
        self.processSliderChange("Sharpness", "Slider", value, "SharpnessSlider")

    def AddGaussianBlurSlider(self, layout):
        self.GaussianBlurSlider = QSlider(QtCore.Qt.Orientation.Horizontal)
        self.GaussianBlurSlider.setRange(0, 2000)
        layout.addRow("Gaussian Blur", self.GaussianBlurSlider)
        self.GaussianBlurSlider.valueChanged.connect(self.OnGaussianBlurChanged)

    def OnGaussianBlurChanged(self, value):
        self.GaussianBlurRadius = value
        self.processSliderChange("Gaussian Blur", "Slider", value, "GaussianBlurSlider")

    def UpdateHistogramPlot(self):
        # Compute image histogram
        img = self.QPixmapToImage(self.image_viewer.pixmap())
        r, g, b, a = img.split()
        r_histogram = r.histogram()
        g_histogram = g.histogram()
        b_histogram = b.histogram()

        # ITU-R 601-2 luma transform:
        luma_histogram = [sum(x) for x in zip([item * float(299/1000) for item in r_histogram],
                                              [item * float(587/1000) for item in g_histogram],
                                              [item * float(114/1000) for item in b_histogram])]

        # Update histogram plot
        self.ImageHistogramGraphRed.setData(y=r_histogram)
        self.ImageHistogramGraphGreen.setData(y=g_histogram)
        self.ImageHistogramGraphBlue.setData(y=b_histogram)
        self.ImageHistogramGraphLuma.setData(y=luma_histogram)

    @QtCore.pyqtSlot()
    def onUpdateImageCompleted(self):
        if self.sliderChangedPixmap:
            self.image_viewer.setImage(self.sliderChangedPixmap, False, self.sliderExplanationOfChange, 
                                       self.sliderTypeOfChange, self.sliderValueOfChange, self.sliderObjectOfChange)
            self.UpdateHistogramPlot()

    def timerEvent(self, event):
        self.killTimer(self.timer_id)
        self.timer_id = -1

        Pixmap = self.image_viewer.getCurrentLayerLatestPixmap()
        OriginalPixmap = Pixmap.copy()

        # TODO: If a selection is active
        # Only apply changes to the selected region
        if self.image_viewer._isSelectingRect:
            print(self.image_viewer._selectRect)
            Pixmap = Pixmap.copy(self.image_viewer._selectRect.toRect())
        elif self.image_viewer._isSelectingPath:
            Pixmap = self.image_viewer.getSelectedRegionAsPixmap()

        if Pixmap:
            if self.RedFactor != 100:
                Pixmap = self.UpdateReds(Pixmap, float(self.RedFactor / 100))
            if self.GreenFactor != 100:
                Pixmap = self.UpdateGreens(Pixmap, float(self.GreenFactor / 100))
            if self.BlueFactor != 100:
                Pixmap = self.UpdateBlues(Pixmap, float(self.BlueFactor / 100))
            if self.Color != 100:
                Pixmap = self.EnhanceImage(Pixmap, ImageEnhance.Color, self.Color)
            if self.Brightness != 100:
                Pixmap = self.EnhanceImage(Pixmap, ImageEnhance.Brightness, self.Brightness)
            if self.Contrast != 100:
                Pixmap = self.EnhanceImage(Pixmap, ImageEnhance.Contrast, self.Contrast)
            if self.Sharpness != 100:
                Pixmap = self.EnhanceImage(Pixmap, ImageEnhance.Sharpness, self.Sharpness)
            if self.GaussianBlurRadius > 0:
                Pixmap = self.ApplyGaussianBlur(Pixmap, float(self.GaussianBlurRadius / 100))

            if self.image_viewer._isSelectingRect:
                painter = QtGui.QPainter(OriginalPixmap)
                selectRect = self.image_viewer._selectRect
                point = QtCore.QPoint(int(selectRect.x()), int(selectRect.y()))
                painter.drawPixmap(point, Pixmap)
                painter.end()
                Pixmap = OriginalPixmap
            elif self.image_viewer._isSelectingPath:
                painter = QtGui.QPainter(OriginalPixmap)
                painter.drawPixmap(QtCore.QPoint(), Pixmap)
                painter.end()
                Pixmap = OriginalPixmap

            self.sliderChangedPixmap = Pixmap
            self.sliderExplanationOfChange = self.sliderExplanationOfChange
            self.sliderTypeOfChange = self.sliderTypeOfChange
            self.sliderValueOfChange = self.sliderValueOfChange
            self.sliderObjectOfChange = self.sliderObjectOfChange
            self.sliderChangeSignal.emit()

    def RemoveRenderedCursor(self):
        # The cursor overlay is being rendered in the view
        # Remove it
        if any([self.image_viewer._isBlurring, self.image_viewer._isRemovingSpots]):
            pixmap = self.getCurrentLayerLatestPixmap()
            self.image_viewer.setImage(pixmap, False)

    def InitTool(self):
        self.RemoveRenderedCursor()

    def OnCursorToolButton(self, checked):
        self.InitTool()
        self.EnableTool("cursor") if checked else self.DisableTool("cursor")

    
    def OnHistogramToolButton(self, checked):
        if checked:
            self.InitTool()
            class HistogrmaWidget(QtWidgets.QWidget):
                def __init__(self, parent, mainWindow):
                    QtWidgets.QWidget.__init__(self, parent)
                    self.parent = parent
                    self.closed = False
                    self.mainWindow = mainWindow

                def closeEvent(self, event):
                    self.destroyed.emit()
                    event.accept()
                    self.closed = True
                    self.mainWindow.DisableTool("histogram")
            if not self.HistogramContent:
                self.HistogramContent = HistogrmaWidget(None, self)
                self.HistogramLayout = QtWidgets.QVBoxLayout(self.HistogramContent)
                self.HistogramLayout.addWidget(self.ImageHistogramPlot)
                self.HistogramContent.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
            self.ImageHistogramPlot.show()
            self.HistogramContent.show()
            # Create a local event loop for this widget
            loop = QtCore.QEventLoop()
            self.HistogramContent.destroyed.connect(loop.quit)
            loop.exec() # wait
        else:
            self.DisableTool("histogram")
            self.HistogramContent.hide()
            #del self.HistogramContent
            #del self.HistogramLayout

    def OnRotateToolButton(self, checked):
        if checked:
            self.InitTool()
            pixmap = self.getCurrentLayerLatestPixmap()
            pil = self.QPixmapToImage(pixmap)
            pil = pil.rotate(90, expand=True)
            updatedPixmap = self.ImageToQPixmap(pil)
            self.image_viewer.setImage(updatedPixmap, True, "Rotate Left", "Tool", None, None)
        self.RotateToolButton.setChecked(False)

       
    def OnFlipLeftRightToolButton(self, checked):
        if checked:
            self.InitTool()
            pixmap = self.getCurrentLayerLatestPixmap()
            pil = self.QPixmapToImage(pixmap)
            pil = pil.transpose(Image.FLIP_LEFT_RIGHT)
            updatedPixmap = self.ImageToQPixmap(pil)
            self.image_viewer.setImage(updatedPixmap, True, "Flip Left-Right", "Tool", None, None)
        self.FlipLeftRightToolButton.setChecked(False)

    def OnFlipTopBottomToolButton(self, checked):
        if checked:
            self.InitTool()
            pixmap = self.getCurrentLayerLatestPixmap()
            pil = self.QPixmapToImage(pixmap)
            pil = pil.transpose(Image.FLIP_TOP_BOTTOM)
            updatedPixmap = self.ImageToQPixmap(pil)
            self.image_viewer.setImage(updatedPixmap, True, "Flip Top-Bottom", "Tool", None, None)
        self.FlipTopBottomToolButton.setChecked(False)

    
    @QtCore.pyqtSlot()
    def onWhiteBalanceCompleted(self, tool):
        output = tool.output
        if output is not None:
            # Save new pixmap
            updatedPixmap = self.ImageToQPixmap(output)
            self.image_viewer.setImage(updatedPixmap, True, "White Balance")

        self.WhiteBalanceToolButton.setChecked(False)
        del tool
        tool = None

    def OnWhiteBalanceToolButton(self, checked):
        if checked:
            self.InitTool()
            currentPixmap = self.getCurrentLayerLatestPixmap()
            image = self.QPixmapToImage(currentPixmap)

            from QToolWhiteBalance import QToolWhiteBalance
            widget = QToolWhiteBalance(None, image, self.onWhiteBalanceCompleted)
            widget.show()

    def OnSlidersToolButton(self, checked):
        if checked:
            self.InitTool()
            class SlidersScrollWidget(QtWidgets.QScrollArea):
                def __init__(self, parent, mainWindow):
                    QtWidgets.QScrollArea.__init__(self, parent)
                    self.parent = parent
                    self.closed = False
                    self.mainWindow = mainWindow

                def closeEvent(self, event):
                    self.destroyed.emit()
                    event.accept()
                    self.closed = True
                    self.mainWindow.SlidersToolButton.setChecked(False)
                    self.mainWindow.image_viewer.setImage(self.mainWindow.image_viewer.pixmap(), True, "Sliders")

            self.slidersScroll = SlidersScrollWidget(None, self)
            self.slidersContent = QtWidgets.QWidget()
            self.slidersScroll.setWidget(self.slidersContent)
            self.slidersScroll.setWidgetResizable(True)
            self.slidersLayout = QtWidgets.QFormLayout(self.slidersContent)

            # Filter sliders
            filter_label = QLabel("Basic")
            self.slidersLayout.addWidget(filter_label)
        
            # Enhance sliders
            self.AddRedColorSlider(self.slidersLayout)
            self.AddGreenColorSlider(self.slidersLayout)
            self.AddBlueColorSlider(self.slidersLayout)
            self.AddColorSlider(self.slidersLayout)
            self.AddBrightnessSlider(self.slidersLayout)
            self.AddContrastSlider(self.slidersLayout)
            self.AddSharpnessSlider(self.slidersLayout)

            # State of enhance sliders
            self.RedFactor = 100
            self.GreenFactor = 100
            self.BlueFactor = 100
            self.Color = 100
            self.Brightness = 100
            self.Contrast = 100
            self.Sharpness = 100

            # Filter sliders
            filter_label = QLabel("Filter")
            self.slidersLayout.addWidget(filter_label)

            # State of filter sliders
            self.GaussianBlurRadius = 0

            self.AddGaussianBlurSlider(self.slidersLayout)

            self.slidersScroll.setStyleSheet('''
                background-color: rgb(44, 44, 44);
            ''')
            self.slidersScroll.setMinimumWidth(300)
            self.slidersScroll.setWindowTitle("Adjust")

            self.slidersScroll.show()

            # Create a local event loop for this widget
            loop = QtCore.QEventLoop()
            self.slidersScroll.destroyed.connect(loop.quit)
            loop.exec() # wait
        else:
            self.slidersScroll.hide()

        self.SlidersToolButton.setChecked(False)

    def OnCurveEditorToolButton(self, checked):
        if checked:
            self.InitTool()
            self.CurveWidget = QCurveWidget.QCurveWidget(None, self.image_viewer)
            self.CurveWidget.setWindowModality(Qt.WindowModality.ApplicationModal)
            self.CurveWidget.show()

            # Create a local event loop for this widget
            loop = QtCore.QEventLoop()
            self.CurveWidget.destroyed.connect(loop.quit)
            loop.exec() # wait
        else:
            self.CurveWidget.hide()

        self.CurveEditorToolButton.setChecked(False)

    def OnInstagramFiltersToolButton(self, checked):
        if checked:
            self.InitTool()

            class QInstagramToolDockWidget(QtWidgets.QDockWidget):
                def __init__(self, parent, mainWindow):
                    QtWidgets.QDockWidget.__init__(self, parent)
                    self.parent = parent
                    self.closed = False
                    self.mainWindow = mainWindow
                    self.setWindowTitle("Filters")

                def closeEvent(self, event):
                    self.destroyed.emit()
                    event.accept()
                    self.closed = True
                    self.mainWindow.InstagramFiltersToolButton.setChecked(False)
                    self.mainWindow.image_viewer.setImage(self.mainWindow.image_viewer.pixmap(), True, "Instagram Filters")

            self.EnableTool("instagram_filters") if checked else self.DisableTool("instagram_filters")
            currentPixmap = self.getCurrentLayerLatestPixmap()
            image = self.QPixmapToImage(currentPixmap)

            from QToolInstagramFilters import QToolInstagramFilters
            tool = QToolInstagramFilters(self, image)
            self.filtersDock = QInstagramToolDockWidget(None, self)
            self.filtersDock.setWidget(tool)
            self.addDockWidget(QtCore.Qt.DockWidgetArea.BottomDockWidgetArea, self.filtersDock)

            widget = self.filtersDock

            widget.show()

            # Create a local event loop for this widget
            loop = QtCore.QEventLoop()
            self.filtersDock.destroyed.connect(loop.quit)
            tool.destroyed.connect(loop.quit)
            loop.exec() # wait
        else:
            self.DisableTool("instagram_filters")
            self.filtersDock.hide()

    
    def EnableTool(self, tool):
        for key, value in self.tools.items():
            if key == tool:
                button = getattr(self, value["tool"])
                button.setChecked(True)
                self.setToolButtonStyleChecked(button)
                setattr(self.image_viewer, value["var"], True)
            else:
                # Disable the other tools
                button = getattr(self, value["tool"])
                button.setChecked(False)
                self.setToolButtonStyleUnchecked(button)
                setattr(self.image_viewer, value["var"], False)
                if "destructor" in value:
                    getattr(self.image_viewer, value["destructor"])()

    def DisableTool(self, tool):
        value = self.tools[tool]
        button = getattr(self, value["tool"])
        button.setChecked(False)
        self.setToolButtonStyleUnchecked(button)
        setattr(self.image_viewer, value["var"], False)
        if "destructor" in value:
            getattr(self.image_viewer, value["destructor"])()

        if tool in ["blur", "spot_removal"]:
            # The cursor overlay is being rendered in the view
            # Remove it
            pixmap = self.getCurrentLayerLatestPixmap()
            self.image_viewer.setImage(pixmap, False)

    def DisableAllTools(self):
        for _, value in self.tools.items():
            getattr(self, value["tool"]).setChecked(False)
            setattr(self.image_viewer, value["var"], False)
            if "destructor" in value:
                getattr(self.image_viewer, value["destructor"])()

    def updateHistogram(self):
        # Update Histogram

        # Compute image histogram
        img = self.QPixmapToImage(self.getCurrentLayerLatestPixmap())
        r, g, b, a = img.split()
        r_histogram = r.histogram()
        g_histogram = g.histogram()
        b_histogram = b.histogram()
        
        # ITU-R 601-2 luma transform:
        luma_histogram = [sum(x) for x in zip([item * float(299/1000) for item in r_histogram],
                                              [item * float(587/1000) for item in g_histogram],
                                              [item * float(114/1000) for item in b_histogram])]

        # Create histogram plot
        x = list(range(len(r_histogram)))
        self.ImageHistogramPlot.removeItem(self.ImageHistogramGraphRed)
        self.ImageHistogramPlot.removeItem(self.ImageHistogramGraphGreen)
        self.ImageHistogramPlot.removeItem(self.ImageHistogramGraphBlue)
        self.ImageHistogramPlot.removeItem(self.ImageHistogramGraphLuma)
        self.ImageHistogramGraphRed = pg.PlotCurveItem(x = x, y = r_histogram, fillLevel=2, width = 1.0, brush=(255,0,0,80))
        self.ImageHistogramGraphGreen = pg.PlotCurveItem(x = x, y = g_histogram, fillLevel=2, width = 1.0, brush=(0,255,0,80))
        self.ImageHistogramGraphBlue = pg.PlotCurveItem(x = x, y = b_histogram, fillLevel=2, width = 1.0, brush=(0,0,255,80))
        self.ImageHistogramGraphLuma = pg.PlotCurveItem(x = x, y = luma_histogram, fillLevel=2, width = 1.0, brush=(255,255,255,80))
        self.ImageHistogramPlot.addItem(self.ImageHistogramGraphRed)
        self.ImageHistogramPlot.addItem(self.ImageHistogramGraphGreen)
        self.ImageHistogramPlot.addItem(self.ImageHistogramGraphBlue)
        self.ImageHistogramPlot.addItem(self.ImageHistogramGraphLuma)

    def OnOpen(self):
        # Load an image file to be displayed (will popup a file dialog).

        self.image_viewer.open()
        if self.image_viewer._current_filename != None:
            size = self.image_viewer.currentPixmapSize()
            if size:
                w, h = size.width(), size.height()
                self.statusBar.showMessage(str(w) + "x" + str(h))
            self.InitTool()
            self.DisableAllTools()
            filename = self.image_viewer._current_filename
            filename = os.path.basename(filename)
            # self.image_viewer.OriginalImage = self.image_viewer.pixmap()
            self.updateHistogram()
            for button in self.ToolButtons:
                button.setEnabled(True)

    
    def OnSave(self):
        if self.image_viewer._current_filename.lower().endswith(".nef"):
            # Cannot save pixmap as .NEF (yet)
            # so open SaveAs menu to export as PNG instead
            self.OnSaveAs()
        else:
            self.image_viewer.save()
   
    def OnSaveAs(self):
        name, ext = os.path.splitext(self.image_viewer._current_filename)
        dialog = QFileDialog()
        dialog.setDefaultSuffix("png")
        extension_filter = "Default (*.png);;BMP (*.bmp);;Icon (*.ico);;JPEG (*.jpeg *.jpg);;PBM (*.pbm);;PGM (*.pgm);;PNG (*.png);;PPM (*.ppm);;TIF (*.tif *.tiff);;WBMP (*.wbmp);;XBM (*.xbm);;XPM (*.xpm)"
        name = dialog.getSaveFileName(self, 'Save File', name + ".png", extension_filter)
        self.image_viewer.save(name[0])
        filename = self.image_viewer._current_filename
        filename = os.path.basename(filename)

    def OnUndo(self):
        self.image_viewer.undoCurrentLayerLatestChange()


def main():
    app = QApplication(sys.argv)
    gui = Gui()
    app.setStyleSheet('''
    QWidget {
        background-color: rgb(44, 44, 44);
        color: white;
    }
    QMainWindow { 
        background-color: rgb(44, 44, 44); 
    }
    QGraphicsView { 
        background-color: rgb(47,47, 47); 
    }
    QDockWidget { 
        background-color: rgb(234, 16, 64); 
    }
    QToolButton {
        border-width: 1px;
        border-color: rgb(22, 22, 22);
        color: white;
        background-color: rgb(44, 44, 44);
    }
    QToolButton:pressed {
        border-width: 3px;
        border-color: rgb(235, 64, 52);
        background-color: rgb(44, 44, 44);
        border-style: solid;
    }
    QPushButton {
        border: none;
        color: white;
        background-color: rgb(44, 44, 44);
    }
    QPushButton:pressed {
        border-width: 1px;
        border-color: rgb(22, 22, 22);
        background-color: rgb(22, 22, 22);
        border-style: solid;
    }
    QLabel {
        background-color: rgb(22, 22, 22);
        color: white;
    }
    ''');
    app.setWindowIcon(QtGui.QIcon("icons/logo.png"))
    sys.exit(app.exec())

if __name__ == '__main__':
    # https://stackoverflow.com/questions/71458968/pyqt6-how-to-set-allocation-limit-in-qimagereader
    os.environ['QT_IMAGEIO_MAXALLOC'] = "1024"
    # QtGui.QImageReader.setAllocationLimit(0)

    main()