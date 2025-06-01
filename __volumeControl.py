import numpy as np
import cv2
from _control_base import BaseControl
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

class VolumeControl(BaseControl):
    def __init__(self, smoothing_factor: float = 0.2):
        """
        smoothing_factor: 0~1 사이값. 0에 가까울수록 더 부드럽게(느리게), 
                          1에 가까울수록 즉시 반영 (기본값: 0.2)
        """
        super().__init__()

        # --- 시스템 오디오 인터페이스 초기화 ---
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        self.audio_interface = cast(interface, POINTER(IAudioEndpointVolume))

        # 이 부분은 더이상 데시벨을 쓰지는 않지만, 만약 GetVolumeRange가 필요하다면 보관
        self.min_vol, self.max_vol = self.audio_interface.GetVolumeRange()[0], self.audio_interface.GetVolumeRange()[1]

        # 내부 상태 초기값
        self.vol_level = 50.0           # 현재 볼륨 퍼센티지 (0~100, float)
        self.muted = False              # 음소거 여부
        self.prev_two_hands = False     # 이전 프레임에 두 손 인식 여부
        self.prev_vol_before_mute = 50.0  # 음소거 직전 볼륨 저장

        self.alpha = smoothing_factor   # 스무딩 계수

        # 시작할 때 시스템 볼륨을 vol_level(50%)으로 맞춤
        self.set_volume(self.vol_level)

    def set_volume(self, level: float):
        """
        level: 0~100 사이의 값 → 0.0~1.0 스칼라로 바꿔서 시스템에 적용.
        """
        level = max(0.0, min(100.0, level))
        # 0.0 ~ 1.0 스칼라로 변환
        scalar = level / 100.0
        self.audio_interface.SetMasterVolumeLevelScalar(scalar, None)
        self.vol_level = level

    def toggle_mute(self):
        """Mute 토글: muted 상태 → 음소거 or 해제"""
        if not self.mode_on:
            return

        if not self.muted:
            # 음소거 직전 볼륨 저장
            self.prev_vol_before_mute = self.vol_level
            # 실제 음소거(Mute) 활성화
            self.audio_interface.SetMute(1, None)
            self.muted = True
        else:
            # 음소거 해제
            self.audio_interface.SetMute(0, None)
            # 이전 볼륨 복원
            self.set_volume(self.prev_vol_before_mute)
            self.muted = False

    def process(self, hand_tracker, frame):
        """
        매 프레임마다 호출됨.
        - hand_tracker: HandTracker 인스턴스
        - frame: OpenCV BGR 프레임(반전된 상태)

        반환값: True(볼륨/음소거 상태가 변경되었을 때), False(변경 없음)
        """
        # --- 1) 음소거 토글 로직: 두 손이 인식되고, 이전엔 두 손이 아니었으면 토글 ---
        if self.mode_on and not self.locked:
            num_hands = hand_tracker.get_num_hands()
            if num_hands >= 2 and not self.prev_two_hands:
                self.toggle_mute()
            self.prev_two_hands = (num_hands >= 2)
        else:
            # 모드 꺼짐 or LOCK 상태면 prev_two_hands 초기화
            self.prev_two_hands = False

        # --- 2) 볼륨 제어 로직 ---
        # 모드OFF, LOCK, 또는 음소거 상태면 볼륨 조절 안 함
        if (not self.mode_on) or self.locked or self.muted:
            return False

        # 검지 끝 좌표 얻기
        idx_x, idx_y = hand_tracker.get_index_finger_tip(frame)
        if idx_y is None:
            return False

        frame_h = frame.shape[0]

        # 화면 아래쪽(높은 y) → 볼륨 0%, 위쪽(낮은 y) → 볼륨 100%로 매핑
        inverted_y = frame_h - idx_y
        target_perc = (inverted_y / frame_h) * 100.0

        # 스무딩: 이전 볼륨에서 alpha만큼만 이동
        smoothed = self.vol_level + self.alpha * (target_perc - self.vol_level)

        # 실제 시스템 볼륨 설정 (스칼라 0.0~1.0 방식)
        self.set_volume(smoothed)
        return True

    def display_info(self, frame):
        """
        화면에 Mode/Lock/Muted/Volume %를 그려 줌.
        - frame: OpenCV BGR 프레임(반전된 상태)
        """
        h, w, _ = frame.shape

        # 1) 모드/락/음소거 상태 표시 (좌측 상단)
        mode_text = "Mode: [Volume]" if self.mode_on else "Mode: [None]"
        lock_text = "Locked" if self.locked else "Unlocked"
        mute_text = "MUTED" if self.muted else ""
        status = f"{mode_text} / {lock_text} {mute_text}" if self.mode_on else f"{mode_text}"
        cv2.putText(frame, status, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        # 2) 모드 ON & 음소거 해제 시, 하단에 볼륨 % 표시
        if self.mode_on and not self.muted:
            vol_text = f"Volume: {int(self.vol_level)} %"
            cv2.putText(frame, vol_text, (10, h - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 0, 0), 2)
