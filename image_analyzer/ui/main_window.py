import os
import numpy as np
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QFileDialog, QMessageBox, QLabel, QInputDialog
)
from PyQt6.QtGui import QPixmap, QImage, QFont
from PyQt6.QtCore import Qt
from ui.image_canvas import ImageCanvas
from core.analyzer import ImageAnalyzer


WINDOW_REGISTRY = []

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.analyzer = ImageAnalyzer()
        self.canvas = ImageCanvas()
        self.next_roi_id = 1
        self.supported_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'}
        
        self.setup_ui()
        self.setAcceptDrops(True)
        self.canvas.set_roi_added_callback(self.on_roi_added)

    def setup_ui(self):
        self.setWindowTitle("Image Analyzer")
        self.resize(1200, 800)
        
        # [v1.3 추가기능] 윈도우 전역에 적용되는 스타일시트 (C++ Qt의 qApp->setStyleSheet)
        self.setStyleSheet("""
            QWidget#CentralWidget {
                /* 여백으로 비치게 될 파란색 배경 (VS 테마 포인트 컬러 Thin Blue Line 용도) */
                background-color: #007acc; 
            }
            QWidget#TopBar, QWidget#RightPanel {
                /* 패널 내부의 기본 짙은 배경색 */
                background-color: #252526; 
            }
            QPushButton {
                background-color: #333337;
                color: #f1f1f1;
                border: 1px solid #3e3e42;
                border-radius: 3px;
                padding: 6px 12px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-weight: bold;
            }
            QPushButton:hover {
                /* 호버 시 파란색 테두리 하이라이트 */
                background-color: #1e1e1e;
                border: 1px solid #007acc;
            }
            QPushButton:pressed {
                background-color: #007acc;
                color: #ffffff;
            }
            QLabel {
                color: #cccccc;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        
        central_widget = QWidget()
        central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)
        
        # 틈새 공간이 1픽셀 파란색 선이 되도록 margin=0, spacing=1 적용
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(1)
        
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(1) # 툴바와 캔버스 사이 1px 파란 분리선
        
        tools_layout = QHBoxLayout()
        
        self.btn_open = QPushButton("파일 열기")
        self.btn_open.clicked.connect(self.open_file_dialog)
        
        self.btn_pan_mode = QPushButton("이동 모드")
        self.btn_point_mode = QPushButton("Point 모드")
        self.btn_rect_mode = QPushButton("Rect 모드")
        self.btn_fit_window = QPushButton("화면 맞춤")
        self.btn_clear = QPushButton("전체 ROI 삭제")
        self.btn_save_png = QPushButton("PNG(결과캡처) 저장")
        
        self.btn_pan_mode.clicked.connect(lambda: self.set_mode(0))
        self.btn_point_mode.clicked.connect(lambda: self.set_mode(1))
        self.btn_rect_mode.clicked.connect(lambda: self.set_mode(2))
        self.btn_fit_window.clicked.connect(self.do_fit_window)
        self.btn_clear.clicked.connect(self.clear_rois)
        self.btn_save_png.clicked.connect(self.export_png)
        
        self.mode_label = QLabel("현재 모드: 이동")
        self.mode_label.setStyleSheet("color: #007acc; font-weight: bold; padding-left: 10px;") 
        
        for btn in [self.btn_open, self.btn_pan_mode, self.btn_point_mode, self.btn_rect_mode, 
                    self.btn_fit_window, self.btn_clear, self.btn_save_png, self.mode_label]:
            tools_layout.addWidget(btn)
        
        tools_layout.setContentsMargins(10, 10, 10, 10)
        tools_layout.setSpacing(8)
        
        top_bar_container = QWidget()
        top_bar_container.setObjectName("TopBar")
        top_bar_container.setLayout(tools_layout)
        
        left_layout.addWidget(top_bar_container, stretch=0)
        left_layout.addWidget(self.canvas, stretch=1)
        
        right_panel_container = QWidget()
        right_panel_container.setObjectName("RightPanel")
        self.right_layout = QVBoxLayout(right_panel_container)
        self.right_layout.setContentsMargins(15, 15, 15, 15)
        
        self.lbl_crop_title = QLabel("▶ 선택 영역 (Crop)")
        self.lbl_crop_title.setStyleSheet("font-weight: bold; color: #007acc;")
        self.lbl_crop = QLabel()
        self.lbl_crop.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_crop.setMinimumSize(256, 256)
        self.lbl_crop.setStyleSheet("background-color: #111111; border: 1px solid #333;")
        
        self.lbl_hist_title = QLabel("▶ RGB 히스토그램")
        self.lbl_hist_title.setStyleSheet("font-weight: bold; color: #007acc;")
        self.lbl_hist = QLabel()
        self.lbl_hist.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_hist.setMinimumSize(256, 200)
        self.lbl_hist.setStyleSheet("background-color: #111111; border: 1px solid #333;")
        
        # [v1.4 추가기능] 텍스트 기반 상세 통계 패널
        self.lbl_stats = QLabel("영역을 선택하시면 R, G, B 채널별\n상세 수치(평균, 편차 등)가 출력됩니다.")
        self.lbl_stats.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        # 통계수치이므로 Consolas 폰트나 monospace를 쓰면 열매맞춤이 이쁩니다
        self.lbl_stats.setStyleSheet("background-color: #1e1e1e; color: #cccccc; border: 1px solid #333; padding: 10px; font-family: Consolas, monospace;")
        self.lbl_stats.setWordWrap(True)
        self.lbl_stats.setMinimumHeight(100)
        
        self.right_layout.addWidget(self.lbl_crop_title)
        self.right_layout.addWidget(self.lbl_crop)
        self.right_layout.addSpacing(15)
        self.right_layout.addWidget(self.lbl_hist_title)
        self.right_layout.addWidget(self.lbl_hist)
        self.right_layout.addWidget(self.lbl_stats) # 하단 부착
        self.right_layout.addStretch()
        
        main_layout.addLayout(left_layout, stretch=3)
        main_layout.addWidget(right_panel_container, stretch=1)

    def do_fit_window(self):
        self.canvas.fit_to_window()
        self.canvas.update()

    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "이미지 파일 열기", "", "Images (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
        if file_path:
            self.load_image_file(file_path)

    def load_image_file(self, file_path):
        if self.analyzer.load_image(file_path):
            self.canvas.set_image(self.analyzer.image)
            self.clear_rois()
            self.setWindowTitle(f"Image Analyzer - {os.path.basename(file_path)}")
            return True

        QMessageBox.warning(self, "오류", "이미지 파일을 불러올 수 없습니다.")
        return False

    def dragEnterEvent(self, event):
        if self._get_dropped_image_paths(event.mimeData()):
            self.canvas.set_drop_highlight(True)
            event.acceptProposedAction()
            return
        self.canvas.set_drop_highlight(False)
        event.ignore()

    def dragMoveEvent(self, event):
        if self._get_dropped_image_paths(event.mimeData()):
            self.canvas.set_drop_highlight(True)
            event.acceptProposedAction()
            return
        self.canvas.set_drop_highlight(False)
        event.ignore()

    def dragLeaveEvent(self, event):
        self.canvas.set_drop_highlight(False)
        event.accept()

    def dropEvent(self, event):
        self.canvas.set_drop_highlight(False)
        file_paths = self._get_dropped_image_paths(event.mimeData())
        if not file_paths:
            event.ignore()
            return

        selected_path = self._select_dropped_image_path(file_paths)
        if not selected_path:
            event.ignore()
            return

        new_window = self.open_image_in_new_window(selected_path)
        if new_window is not None:
            event.acceptProposedAction()
            return
        event.ignore()

    def _get_dropped_image_paths(self, mime_data):
        if not mime_data.hasUrls():
            return []

        file_paths = []

        for url in mime_data.urls():
            local_file = url.toLocalFile()
            if not local_file or not os.path.isfile(local_file):
                continue

            if os.path.splitext(local_file)[1].lower() in self.supported_extensions:
                file_paths.append(local_file)

        return file_paths

    def _select_dropped_image_path(self, file_paths):
        if len(file_paths) == 1:
            return file_paths[0]

        items = [os.path.basename(path) for path in file_paths]
        selected_name, ok = QInputDialog.getItem(
            self,
            "드롭한 파일 선택",
            "열 이미지를 선택하세요:",
            items,
            0,
            False
        )
        if not ok:
            return None

        selected_index = items.index(selected_name)
        return file_paths[selected_index]

    def open_image_in_new_window(self, file_path):
        new_window = MainWindow()
        if not new_window.load_image_file(file_path):
            new_window.deleteLater()
            return None

        new_window.move(self.x() + 40, self.y() + 40)
        new_window.show()
        new_window.raise_()
        new_window.activateWindow()
        WINDOW_REGISTRY.append(new_window)
        return new_window

    def set_mode(self, mode):
        self.canvas.set_mode(mode)
        mode_names = ["이동", "Point", "Rect"]
        self.mode_label.setText(f"현재 모드: {mode_names[mode]}")

    def on_roi_added(self, roi_type, rect):
        if self.analyzer.image is None: return
        
        if roi_type == 'Point':
            r, g, b = self.analyzer.get_point_rgb(rect.x(), rect.y())
        else:
            r, g, b = self.analyzer.get_rect_rgb(rect.x(), rect.y(), rect.width(), rect.height())
            
            # [v1.4 수정] analyzer가 넘겨주는 3개의 리턴값 언패킹 (crop_img, hist_img, stats_dict)
            res = self.analyzer.get_crop_and_histogram(
                rect.x(), rect.y(), rect.width(), rect.height()
            )
            if res[0] is not None:
                crop_img, hist_img, stats_dict = res
                self.update_right_panel(crop_img, hist_img, stats_dict)
            
        color = (30, 144, 255) if roi_type == 'Rect' else (255, 69, 0)
        
        roi_data = {
            'id': self.next_roi_id,
            'type': roi_type,
            'rect': rect,
            'color': color,
            'val': (r, g, b)
        }
        self.canvas.rois.append(roi_data)
        self.next_roi_id += 1
        self.canvas.update()

    def numpy_to_qpixmap(self, np_img):
        if not np_img.flags['C_CONTIGUOUS']:
            np_img = np.ascontiguousarray(np_img)
        h, w, c = np_img.shape
        bytes_per_line = c * w
        qimg = QImage(np_img.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(qimg)

    # [v1.4 추가] stats_dict 파라미터 연동
    def update_right_panel(self, crop_img, hist_img, stats_dict=None):
        crop_pix = self.numpy_to_qpixmap(crop_img)
        scaled_crop = crop_pix.scaled(
            self.lbl_crop.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )
        self.lbl_crop.setPixmap(scaled_crop)
        
        hist_pix = self.numpy_to_qpixmap(hist_img)
        self.lbl_hist.setPixmap(hist_pix)
        
        # [v1.4 추가기능] 텍스트 패널에 C++ printf 스타일 가변 포매팅 출력 
        if stats_dict:
            lines = []
            for ch in ['R', 'G', 'B']:
                data = stats_dict[ch]
                lines.append(f"[{ch}] Avg: {data['mean']:.1f} (±{data['std']:.1f})")
                lines.append(f"    Range: {data['min']} ~ {data['max']}")
            self.lbl_stats.setText("\n".join(lines))

    def clear_rois(self):
        self.canvas.clear_rois()
        self.lbl_crop.clear()
        self.lbl_hist.clear()
        self.lbl_stats.setText("영역을 선택하시면 R, G, B 채널별\n상세 수치(평균, 편차 등)가 출력됩니다.")
        self.next_roi_id = 1

    def export_png(self):
        if self.canvas.qpixmap is None: return
        path, _ = QFileDialog.getSaveFileName(self, "PNG 저장", "canvas_capture.png", "PNG Images (*.png)")
        if path:
            pixmap = self.canvas.grab()
            pixmap.save(path, "PNG")
            QMessageBox.information(self, "완료", "화면이 PNG로 성공적으로 캡처/저장되었습니다.")
