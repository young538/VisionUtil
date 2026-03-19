import cv2
import numpy as np

class ImageAnalyzer:
    def __init__(self):
        self.image = None
        self.file_path = None

    def load_image(self, file_path):
        try:
            with open(file_path, 'rb') as f:
                bytes_arr = bytearray(f.read())
                np_array = np.asarray(bytes_arr, dtype=np.uint8)
                image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
                if image is not None:
                    self.image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                    self.file_path = file_path
                    return True
        except Exception as e:
            print(f"이미지 로드 중 에러: {e}")
        return False

    def get_point_rgb(self, x, y):
        # 파이썬 OpenCV의 Mat 배열 인덱싱은 y(행), x(열) 순으로 C++ Mat 객체의 .at<Vec3b>(y, x) 와 동일한 개념입니다.
        if self.image is None: return (0, 0, 0)
        h, w = self.image.shape[:2]
        if 0 <= x < w and 0 <= y < h:
            color = self.image[y, x]
            return (int(color[0]), int(color[1]), int(color[2]))
        return (0, 0, 0)

    def get_rect_rgb(self, x, y, w, h):
        if self.image is None: return (0, 0, 0)
        img_h, img_w = self.image.shape[:2]
        
        x1 = max(0, min(x, x+w))
        x2 = min(img_w, max(x, x+w))
        y1 = max(0, min(y, y+h))
        y2 = min(img_h, max(y, y+h))
        
        if x2 <= x1 or y2 <= y1:
            return (0, 0, 0)
            
        roi = self.image[y1:y2, x1:x2]
        mean_color = cv2.mean(roi)
        return (int(mean_color[0]), int(mean_color[1]), int(mean_color[2]))

    # [v1.2 추가기능] ROI 영역의 도무송 이미지(Crop)와 히스토그램 생성을 처리하는 함수
    def get_crop_and_histogram(self, x, y, w, h):
        if self.image is None: return None, None, None
        img_h, img_w = self.image.shape[:2]
        
        x1 = max(0, min(x, x+w))
        x2 = min(img_w, max(x, x+w))
        y1 = max(0, min(y, y+h))
        y2 = min(img_h, max(y, y+h))
        
        if x2 <= x1 or y2 <= y1:
            return None, None, None
            
        # C++의 cv::Mat(rect) 참조 슬라이싱. Python에서는 메모리 포인터 복사 없이 곧바로 뷰를 리턴합니다.
        roi = self.image[y1:y2, x1:x2] 
        
        # 히스토그램을 그릴 검은색 도화지 메모리 할당 (폭 256, 높이 200, RGB)
        hist_h = 200
        hist_w = 256
        hist_img = np.zeros((hist_h, hist_w, 3), dtype=np.uint8)
        
        max_counts = []
        stats_dict = {}
        
        # self.image는 RGB 포맷으로 로드되었으므로 인덱스 0이 R, 1이 G, 2가 B입니다.
        for i, ch_name in enumerate(['R', 'G', 'B']):
            # C++의 cv::Mat(rect) 개념처럼 채널 슬라이싱
            ch_data = roi[:, :, i]
            
            # C++의 cv::calcHist 동일 호출. 단일 채널(i)의 빈도수(256구간) 추출
            hist = cv2.calcHist([ch_data], [0], None, [256], [0, 256])
            max_counts.append(hist.max())
            
            # [v1.4 추가] 통계 지표 직접 연산 (C++의 cv::meanStdDev와 유사함)
            stats_dict[ch_name] = {
                'mean': float(np.mean(ch_data)),
                'std': float(np.std(ch_data)),
                'min': int(np.min(ch_data)),
                'max': int(np.max(ch_data))
            }
            
            # C++의 cv::normalize 로 Y축 스케일을 0~hist_h 로 맞춥니다 (화면 높이에 맞춰 평탄화)
            cv2.normalize(hist, hist, alpha=0, beta=hist_h, norm_type=cv2.NORM_MINMAX)
            
            pts = []
            # 256개의 분포 선그래프 포인트 생성
            for x_idx in range(256):
                val = int(hist[x_idx][0])
                # 좌상단이 (0,0) 이므로 아래에서 위로 솟게 하려면 hist_h - val 설정
                pts.append((x_idx, hist_h - val))
            pts = np.array(pts, dtype=np.int32)
            
            # RGB 순서에 맞는 전용 펜 컬러 배정
            channel_color = [0, 0, 0]
            channel_color[i] = 255
            
            # C++ cv::polylines 호출
            cv2.polylines(hist_img, [pts], isClosed=False, color=tuple(channel_color), thickness=1)
            
        # [v1.4 추가] 히스토그램 이미지 내부 여백에 Grid(눈금)와 수치 렌더링
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.4
        grid_color = (60, 60, 60)
        text_color = (180, 180, 180)
        
        # X축 3분할 가이드라인
        for x_val in (0, 127, 255):
            cv2.line(hist_img, (x_val, 0), (x_val, hist_h), grid_color, 1, cv2.LINE_AA)
            cv2.putText(hist_img, str(x_val), (max(0, x_val - 12), hist_h - 5), font, font_scale, text_color, 1, cv2.LINE_AA)
            
        # Y축 상한선 픽셀수 (Max 빈도)
        g_max = max(max_counts) if max_counts else 0
        cv2.putText(hist_img, f"MaxPx: {int(g_max)}", (5, 15), font, font_scale, text_color, 1, cv2.LINE_AA)
            
        return roi, hist_img, stats_dict
