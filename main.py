import cv2

from _handTracking import HandTracker
from __volumeControl import VolumeControl
from __zoomControl import ZoomControl
from __screenCapture import ScreenCaptureControl

def main():
    # 1) 웹캠 & HandTracker 초기화
    cap = cv2.VideoCapture(0)
    hand_tracker = HandTracker(max_hands=2)

    # 2) 사용할 컨트롤러 인스턴스화 → key_map에 단축키:컨트롤러 객체 형태로 저장
    volume_ctrl = VolumeControl(smoothing_factor=0.2)
    zoom_ctrl   = ZoomControl(base_size=300, initial_zoom=2.0, zoom_step=0.5)
    capture_ctrl = ScreenCaptureControl()

    # 각 컨트롤러를 토글할 키를 지정
    controls = {
        ord('v'): volume_ctrl,
        ord('z'): zoom_ctrl,
        ord('s'): capture_ctrl
    }

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 3) 좌우 반전 (거울 모드)
        frame = cv2.flip(frame, 1)

        # 4) 손 인식 → self.results에 landmark 저장
        frame = hand_tracker.find_hands(frame, draw=False)

        # 5) 각 컨트롤러에 process 위임
        for ctrl in controls.values():
            ctrl.process(hand_tracker, frame)

        # 6) 활성화된 컨트롤러만 화면에 상태 표시(Mode/Lock/기능별 상태)
        for ctrl in controls.values():
            if ctrl.mode_on:
                ctrl.display_info(frame)

        # 7) 키 입력 처리
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC 누르면 종료
            break

        # 모드 토글: 'v' → VolumeControl 모드 on/off
        if key in controls:
            controls[key].toggle_mode()

        # 락 토글: 스페이스(32) 또는 엔터(13) → 현재 모드 ON인 컨트롤러 lock/unlock
        elif key == 32 or key == 13:
            for ctrl in controls.values():
                if ctrl.mode_on:
                    ctrl.toggle_lock()

        # 줌 모드일 때 배율 증가('+') 및 감소('-')
        elif key in (ord('+'), ord('=')):
            if zoom_ctrl.mode_on:
                zoom_ctrl.increase_zoom()
        elif key == ord('-'):
            if zoom_ctrl.mode_on:
                zoom_ctrl.decrease_zoom()

        # 8) 결과 화면 출력
        cv2.imshow("Gesture-Based Control", frame)

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
