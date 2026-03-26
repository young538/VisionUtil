from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QImage, QPixmap, QColor, QPen
from PyQt6.QtCore import Qt, QRect, QPoint, QRectF
import numpy as np

class ImageCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = None
        self.qpixmap = None
        self.drop_highlight = False
        
        self.scale_factor = 1.0
        self.pan_offset = QPoint(0, 0)
        
        self.last_mouse_pos = QPoint(0, 0)
        self.is_panning = False
        
        self.mode = 0
        self.rois = []
        self.current_rect_start = None
        self.current_rect_end = None
        
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.roi_added_callback = None

    def set_roi_added_callback(self, cb):
        self.roi_added_callback = cb

    def set_mode(self, mode):
        self.mode = mode
        self.current_rect_start = None
        self.current_rect_end = None

    def set_image(self, image_array):
        self.image = image_array
        if self.image is not None:
            if not self.image.flags['C_CONTIGUOUS']:
                self.image = np.ascontiguousarray(self.image)
            h, w, c = self.image.shape
            bytes_per_line = c * w
            q_image = QImage(self.image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            self.qpixmap = QPixmap.fromImage(q_image)
            self.fit_to_window()
            self.update()

    def fit_to_window(self):
        if self.qpixmap is None: return
        widget_rect = self.rect()
        pixmap_rect = self.qpixmap.rect()
        
        rect_ratio = widget_rect.width() / widget_rect.height()
        pix_ratio = pixmap_rect.width() / pixmap_rect.height()
        
        if rect_ratio > pix_ratio:
            self.scale_factor = widget_rect.height() / pixmap_rect.height()
        else:
            self.scale_factor = widget_rect.width() / pixmap_rect.width()
            
        x = int((widget_rect.width() - pixmap_rect.width() * self.scale_factor) / 2)
        y = int((widget_rect.height() - pixmap_rect.height() * self.scale_factor) / 2)
        self.pan_offset = QPoint(x, y)

    def paintEvent(self, event):
        super().paintEvent(event)
        
        painter = QPainter(self)
        
        # [v1.3 추가기능] VS Code 에디터 영역과 동일한 극다크 그레이 적용
        painter.fillRect(self.rect(), QColor(30, 30, 30)) 

        if self.drop_highlight:
            painter.setPen(QPen(QColor(0, 122, 204), 3, Qt.PenStyle.DashLine))
            painter.setBrush(QColor(0, 122, 204, 35))
            painter.drawRect(self.rect().adjusted(6, 6, -6, -6))
        
        if self.qpixmap is None: return
            
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        painter.translate(self.pan_offset)
        painter.scale(self.scale_factor, self.scale_factor)
        
        painter.drawPixmap(0, 0, self.qpixmap)
        
        inverse_scale = 1.0 / self.scale_factor
        
        for roi in self.rois:
            painter.setPen(QPen(QColor(*roi['color']), max(1, 2 * inverse_scale)))
            if roi['type'] == 'Point':
                px, py = roi['rect'].x(), roi['rect'].y()
                s = 5 * inverse_scale
                painter.drawLine(int(px-s), int(py), int(px+s), int(py))
                painter.drawLine(int(px), int(py-s), int(px), int(py+s))
            elif roi['type'] == 'Rect':
                painter.drawRect(roi['rect'])
                
            # [v1.1 추가기능] 오버레이 시각화. 
            # 텍스트가 작아지거나 커지는 것을 막기 위해 뷰/월드 스케일에 맞게 역-보정 (C++에서의 글꼴 배율 역버퍼링 기법과 유사)
            font_size = max(5, int(15 * inverse_scale))
            font = painter.font()
            font.setPixelSize(font_size)
            font.setBold(True)
            painter.setFont(font)
            
            # C++의 QString::asprintf() 처럼 쉽게 포매팅
            text = f"#{roi['id']} (R:{roi['val'][0]}, G:{roi['val'][1]}, B:{roi['val'][2]})"
            
            # 텍스트 가독성을 올려주는 그림자(블랙 브러시)를 먼저 깔고, 진짜 색상 덮어씌우기
            offset = max(1, 1 * inverse_scale)
            text_x = roi['rect'].x()
            
            # 사각형과 점 모드에 따라 텍스트 표시 위치 분기
            if roi['type'] == 'Rect':
                text_y = roi['rect'].y() + roi['rect'].height() + int(18 * inverse_scale)
            else:
                text_y = roi['rect'].y() - int(5 * inverse_scale)
            
            painter.setPen(QPen(QColor(0, 0, 0), 1))
            painter.drawText(int(text_x + offset), int(text_y + offset), text)
            
            painter.setPen(QPen(QColor(0, 255, 255) if roi['type']=='Rect' else QColor(255, 230, 230), 1))
            painter.drawText(int(text_x), int(text_y), text)

        # 드래그 중인 임시 라인
        if self.mode == 2 and self.current_rect_start and self.current_rect_end:
            painter.setPen(QPen(QColor(0, 255, 0), max(1, 2 * inverse_scale), Qt.PenStyle.DashLine))
            r = QRect(self.current_rect_start, self.current_rect_end).normalized()
            painter.drawRect(r)

    def screen_to_image(self, pos):
        x = (pos.x() - self.pan_offset.x()) / self.scale_factor
        y = (pos.y() - self.pan_offset.y()) / self.scale_factor
        return QPoint(int(x), int(y))

    def wheelEvent(self, event):
        if self.qpixmap is None: return
        
        zoom_in_factor = 1.2
        zoom_out_factor = 1.0 / zoom_in_factor
        
        mouse_pos = event.position().toPoint()
        old_img_pos = self.screen_to_image(mouse_pos)
        
        if event.angleDelta().y() > 0:
            self.scale_factor *= zoom_in_factor
        else:
            self.scale_factor *= zoom_out_factor
            
        self.scale_factor = max(0.05, min(self.scale_factor, 50.0))
        
        new_x = mouse_pos.x() - old_img_pos.x() * self.scale_factor
        new_y = mouse_pos.y() - old_img_pos.y() * self.scale_factor
        self.pan_offset = QPoint(int(new_x), int(new_y))
        
        self.update()

    def mousePressEvent(self, event):
        if self.qpixmap is None: return
        
        # [v1.1 추가기능] 캔버스 우클릭 이벤트를 이용해 특정 ROI 삭제 (C++의 Qt::RightButton 처리와 동일)
        if event.button() == Qt.MouseButton.RightButton:
            img_pos = self.screen_to_image(event.pos())
            self.delete_roi_at(img_pos)
            return
            
        if event.button() == Qt.MouseButton.MiddleButton or self.mode == 0:
            self.is_panning = True
            self.last_mouse_pos = event.pos()
        elif event.button() == Qt.MouseButton.LeftButton:
            img_pos = self.screen_to_image(event.pos())
            if self.mode == 1:
                self.add_point_roi(img_pos)
            elif self.mode == 2:
                self.current_rect_start = img_pos
                self.current_rect_end = img_pos

    # [v1.1 추가기능] 클릭한 위치 기반으로 삭제
    def delete_roi_at(self, img_pos):
        # 최상단(가장 나중에 겹쳐 그린 것)부터 검사하기 위해 뒤부터 순회. C++의 rbegin()
        for i in reversed(range(len(self.rois))):
            roi = self.rois[i]
            r = roi['rect']
            if roi['type'] == 'Rect':
                # C++의 QRect::contains() 와 동일
                if r.contains(img_pos):
                    del self.rois[i]
                    self.update()
                    return
            elif roi['type'] == 'Point':
                dx = abs(r.x() - img_pos.x())
                dy = abs(r.y() - img_pos.y())
                # 마우스 컨트롤 편의성을 위해 약간의 판정 여유 범위(hitbox)를 부여
                hitbox = max(5, 5 / self.scale_factor)
                if dx < hitbox and dy < hitbox:
                    del self.rois[i]
                    self.update()
                    return

    def mouseMoveEvent(self, event):
        if self.qpixmap is None: return
        
        if self.is_panning:
            delta = event.pos() - self.last_mouse_pos
            self.pan_offset += delta
            self.last_mouse_pos = event.pos()
            self.update()
        elif self.mode == 2 and self.current_rect_start is not None:
            self.current_rect_end = self.screen_to_image(event.pos())
            self.update()

    def mouseReleaseEvent(self, event):
        if self.is_panning:
            self.is_panning = False
        
        if event.button() == Qt.MouseButton.LeftButton and self.mode == 2 and self.current_rect_start:
            r = QRect(self.current_rect_start, self.current_rect_end).normalized()
            if r.width() > 1 and r.height() > 1:
                self.add_rect_roi(r)
            self.current_rect_start = None
            self.current_rect_end = None
            self.update()

    def add_point_roi(self, pos):
        if self.roi_added_callback:
            self.roi_added_callback('Point', QRect(pos, pos))

    def add_rect_roi(self, rect):
        if self.roi_added_callback:
            self.roi_added_callback('Rect', rect)
            
    def clear_rois(self):
        self.rois.clear()
        self.update()

    def set_drop_highlight(self, enabled):
        if self.drop_highlight == enabled:
            return
        self.drop_highlight = enabled
        self.update()
