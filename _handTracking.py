import cv2
import mediapipe as mp

class HandTracker:
    def __init__(self, max_hands=2, detection_conf=0.7, tracking_conf=0.7):
        """
        max_hands=2로 하면 한 번에 두 손까지 인식 가능.
        """
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(max_num_hands=max_hands,
                                         min_detection_confidence=detection_conf,
                                         min_tracking_confidence=tracking_conf)
        self.mp_draw = mp.solutions.drawing_utils
        self.results = None

    def find_hands(self, frame, draw=False):
        """
        frame (BGR)을 받아서 MediaPipe로 손 인식 → self.results에 저장.
        draw=True면 landmark와 연결을 frame 위에 그림.
        → 매 프레임 호출해야 함.
        """
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.results = self.hands.process(img_rgb)

        if self.results.multi_hand_landmarks and draw:
            for hand_lms in self.results.multi_hand_landmarks:
                self.mp_draw.draw_landmarks(frame, hand_lms, self.mp_hands.HAND_CONNECTIONS)
        return frame

    def get_index_finger_tip(self, frame):
        """
        첫 번째 인식된 손의 검지 끝(landmark #8) 픽셀 좌표를 반환.
        - frame: BGR 프레임 (거울 모드 적용된 상태)
        - 인식 실패 시 (None, None)
        """
        if self.results and self.results.multi_hand_landmarks:
            hand_lm = self.results.multi_hand_landmarks[0]
            h, w, _ = frame.shape
            idx_tip = hand_lm.landmark[8]
            x, y = int(idx_tip.x * w), int(idx_tip.y * h)
            return x, y
        return None, None

    def get_num_hands(self):
        """
        현재 프레임에서 인식된 손 개수 반환 (0~2).
        """
        if self.results and self.results.multi_hand_landmarks:
            return len(self.results.multi_hand_landmarks)
        return 0
