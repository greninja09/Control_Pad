import cv2
import numpy as np
import ctypes
from ctypes import wintypes
from _control_base import BaseControl
import mss

# Win32 API 상수 및 함수 준비
user32 = ctypes.windll.user32

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class ZoomControl(BaseControl):
    def __init__(self, base_size: int = 300, initial_zoom: float = 2.0, zoom_step: float = 0.5):
        """
        base_size: 돋보기 창의 한 변 길이 (픽셀)
        initial_zoom: 돋보기 초기 배율 (예: 2.0배)
        zoom_step: 배율 조정 단위
        """
        super().__init__()
        self.base_size = base_size
        self.zoom_factor = initial_zoom
        self.zoom_step = zoom_step

        # 한 번 캡처된 원본 이미지를 저장할 변수
        self.zoomed_original = None

        # 돋보기 창 설정
        self.zoom_window = "Magnifier"
        cv2.namedWindow(self.zoom_window)

        # mss 객체 (화면 캡처용)
        self.sct = mss.mss()

    def get_cursor_pos(self):
        """
        현재 마우스 커서 위치(x, y)를 반환.
        """
        pt = POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y

    def set_cursor_pos(self, x, y):
        """
        마우스 커서를 (x, y)로 이동.
        """
        user32.SetCursorPos(int(x), int(y))

    def increase_zoom(self):
        """
        줌 배율을 +zoom_step 만큼 증가(최대 5.0배).
        """
        self.zoom_factor = min(self.zoom_factor + self.zoom_step, 5.0)

    def decrease_zoom(self):
        """
        줌 배율을 -zoom_step 만큼 감소(최소 1.0배).
        """
        self.zoom_factor = max(self.zoom_factor - self.zoom_step, 1.0)

    def capture_screen_region(self, center_x, center_y, half_size):
        """
        mss를 이용해 화면에서 (center_x±half_size, center_y±half_size) 영역만 캡처하여
        numpy 배열(BGR)로 반환.
        """
        left = int(center_x - half_size)
        top = int(center_y - half_size)
        width = int(2 * half_size)
        height = int(2 * half_size)

        # 화면 해상도와 비교해서 범위 클램핑
        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)
        if left < 0:
            left = 0
        if top < 0:
            top = 0
        if left + width > screen_w:
            width = screen_w - left
        if top + height > screen_h:
            height = screen_h - top

        monitor = {"left": left, "top": top, "width": width, "height": height}
        img = self.sct.grab(monitor)

        # mss가 반환하는 이미지는 BGRA 형식, numpy 배열로 변환 후 BGR만 사용
        arr = np.array(img)  
        arr = arr[..., :3]  # BGRA → BGR
        return arr

    def process(self, hand_tracker, frame):
        """
        매 프레임 호출됨.
        - hand_tracker: HandTracker 인스턴스 (이미 웹캠 프레임에 find_hands 적용됨)
        - frame: OpenCV BGR 웹캠 프레임 (거울 모드)

        동작:
        1) mode_on이 False면 빈 창 표시
        2) 손가락 위치로 커서 이동 (mode_on=True & locked=False)
        3) locked가 False이거나 zoomed_original이 None이면, 
           기존에 저장된 zoomed_original이 있으면 그대로 표시 후 반환
        4) locked=True & zoomed_original이 이미 저장되어 있으면, 
           그 이미지를 현재 zoom_factor 배율로 resize 후 표시
        """
        # 1) 모드가 꺼져 있으면 돋보기 창을 빈 화면으로
        if not self.mode_on:
            cv2.imshow(self.zoom_window, np.zeros((1, 1), dtype=np.uint8))
            self.zoomed_original = None
            return False

        # 2) 손가락 위치 → 화면 좌표로 환산 → 커서 이동
        idx_x, idx_y = hand_tracker.get_index_finger_tip(frame)
        frame_h, frame_w = frame.shape[:2]
        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)

        if idx_x is not None and idx_y is not None and not self.locked:
            sx = int((idx_x / frame_w) * screen_w)
            sy = int((idx_y / frame_h) * screen_h)
            self.set_cursor_pos(sx, sy)
            self.prev_pos = (sx, sy)
        elif self.locked and hasattr(self, "prev_pos") and self.prev_pos:
            sx, sy = self.prev_pos
        else:
            # 손을 인식 못 하면 돋보기 창을 빈 화면으로
            cv2.imshow(self.zoom_window, np.zeros((1, 1), dtype=np.uint8))
            return False

        # 3) 아직 락이 걸리지 않았거나 zoomed_original이 없는 상태
        if not self.locked or self.zoomed_original is None:
            if self.zoomed_original is not None:
                cv2.imshow(self.zoom_window, self.zoomed_original)
            return False

        # 4) 락 상태 & zoomed_original 저장된 상태 → 배율만 조절해서 표시
        zoomed_resized = cv2.resize(
            self.zoomed_original,
            (self.base_size, self.base_size),
            interpolation=cv2.INTER_LINEAR
        )
        cv2.imshow(self.zoom_window, zoomed_resized)
        return True

    def display_info(self, frame):
        """
        메인 카메라 프레임 위에 “Mode / Lock / Zoom 배율” 텍스트 표시
        """
        h, w = frame.shape[:2]
        mode_text = "Mode: [Zoom]" if self.mode_on else "Mode: [None]"
        lock_text = "Locked" if self.locked else "Unlocked"
        txt = f"{mode_text} / {lock_text}" if self.mode_on else f"{mode_text}"
        cv2.putText(frame, txt, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        if self.mode_on:
            cv2.putText(frame, f"Zoom: {self.zoom_factor:.1f}x", (10, h - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

    def toggle_lock(self):
        """
        스페이스바(또는 Enter)로 캡처 모드 토글
        - locked=False → True: 현재 cursor_pos 기준으로 한번만 캡처하여 zoomed_original에 저장
        - locked=True → False: zoomed_original을 None으로 만들어 다음 캡처 준비
        """
        if not self.mode_on:
            return

        self.locked = not self.locked
        if self.locked:
            sx, sy = self.prev_pos
            half = int(self.base_size / (2 * self.zoom_factor))
            # mss를 이용하여 화면을 캡처
            self.zoomed_original = self.capture_screen_region(sx, sy, half)
        else:
            self.zoomed_original = None
