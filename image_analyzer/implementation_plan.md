# 뼈대 생성 구현 계획

## 1. 개요
`AGENTS.md`의 개발 단계 1항목 **"뼈대 생성 (폴더 구조 + 클래스 시그니처 + 빈 창)"** 을 구현하기 위한 단계별 계획입니다.

## 2. 생성할 폴더 및 파일 구조
```text
image_analyzer/
├── main.py
├── requirements.txt
├── ui/
│   ├── __init__.py
│   ├── main_window.py
│   └── image_canvas.py
└── core/
    ├── __init__.py
    └── analyzer.py
```

## 3. 파일별 구현 내용 (클래스/함수 시그니처)

### `requirements.txt`
지정된 기술 스택 버전을 고정합니다.
- `PyQt6~=6.7.0`
- `opencv-python~=4.10.0`
- `numpy~=1.26.0`

### `ui/image_canvas.py`
이미지를 표시하고 이벤트를 처리할 캔버스 위젯 (내부 로직은 `pass` 처리)
- `class ImageCanvas(QWidget):`
  - `def __init__(self, parent=None):`
  - `def set_image(self, image):`
  - `def wheelEvent(self, event):`
  - `def mousePressEvent(self, event):`
  - `def mouseMoveEvent(self, event):`
  - `def mouseReleaseEvent(self, event):`
  - `def paintEvent(self, event):`

### `ui/main_window.py`
툴바(기능 버튼들)와 캔버스, 정보 패널을 담는 메인 윈도우 UI 클래스 (내부 로직은 `pass` 처리)
- `class MainWindow(QMainWindow):`
  - `def __init__(self):`
  - `def setup_ui(self):`
  - `def open_file_dialog(self):`
  - `def set_point_mode(self):`
  - `def set_rect_mode(self):`
  - `def clear_rois(self):`
  - `def export_csv(self):`
  - `def export_png(self):`

### `core/analyzer.py`
이미지 로딩 및 RGB 분석 기능을 담당하는 코어 클래스 (내부 로직은 `pass` 처리)
- `class ImageAnalyzer:`
  - `def __init__(self):`
  - `def load_image(self, file_path):`
  - `def get_point_rgb(self, x, y):`
  - `def get_rect_rgb(self, x, y, w, h):`

### `main.py`
애플리케이션 진입점.
빈 창이 뜨는지 확인할 수 있도록 `QApplication` 생성, `MainWindow` 인스턴스화 후 `show()`를 호출합니다.

### `PROGRESS.md`
뼈대 생성이 완료되면 진행 상황을 반영하도록 해당 파일을 업데이트합니다.

## 4. 실행 및 검증
위 파일들의 생성이 마무리되면 터미널에서 아래 명령을 실행하여 **빈 창이 정상적으로 표시**되는지 검증합니다.
```bash
python main.py
```
