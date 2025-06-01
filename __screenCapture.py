import cv2
import pyautogui
import datetime
import os
from _control_base import BaseControl

class ScreenCaptureControl(BaseControl):
    def __init__(self):
        super().__init__()
        self.prev_palm_open = False
        self.feedback_frames = 0
        self.feedback_pos = (0, 0)
        self.save_dir = "captures"
        os.makedirs(self.save_dir, exist_ok=True)

    def fingers_extended(self, hand_landmarks, frame):
        h, w, _ = frame.shape
        lm = hand_landmarks.landmark

        # 검지, 중지, 약지, 소지 (tip.y < pip.y) 모두 펼침
        for tip_id, pip_id in zip([8, 12, 16, 20], [6, 10, 14, 18]):
            if (lm[tip_id].y * h) > (lm[pip_id].y * h):
                return False
        # 엄지 펼침: 거울 모드 기준으로 tip.x > ip.x
        if (lm[4].x * w) < (lm[3].x * w):
            return False
        return True

    def process(self, hand_tracker, frame):
        if not self.mode_on or self.locked:
            self.prev_palm_open = False
            return False

        results = hand_tracker.results
        if not results or not results.multi_hand_landmarks:
            self.prev_palm_open = False
            return False

        hand_lms = results.multi_hand_landmarks[0]
        h, w, _ = frame.shape
        palm_open = self.fingers_extended(hand_lms, frame)

        if palm_open and not self.prev_palm_open:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.save_dir, f"capture_{timestamp}.png")
            img = pyautogui.screenshot()
            img.save(filename)

            x = int(hand_lms.landmark[0].x * w)
            y = int(hand_lms.landmark[0].y * h)
            self.feedback_pos = (x, y)
            self.feedback_frames = 5
            self.prev_palm_open = True
            return True

        if not palm_open:
            self.prev_palm_open = False

        if self.feedback_frames > 0:
            overlay = frame.copy()
            x, y = self.feedback_pos
            cv2.circle(overlay, (x, y), 30, (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)
            self.feedback_frames -= 1

        return False

    def display_info(self, frame):
        h, w, _ = frame.shape
        mode_text = "Mode: [Capture]" if self.mode_on else "Mode: [None]"
        lock_text = "Locked" if self.locked else "Unlocked"
        txt = f"{mode_text} / {lock_text}" if self.mode_on else f"{mode_text}"
        cv2.putText(frame, txt, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
