import abc

class BaseControl(abc.ABC):
    def __init__(self):
        # 전체 컨트롤러가 공통으로 가지는 상태
        self.mode_on = False    # 모드 ON/OFF
        self.locked = False     # LOCK(고정) ON/OFF

    def toggle_mode(self):
        """모드 ON/OFF 토글"""
        self.mode_on = not self.mode_on
        # 모드를 껐다가 다시 켜면, 잠금은 자동 해제되도록 기본 동작
        if not self.mode_on:
            self.locked = False

    def toggle_lock(self):
        """LOCK(고정) ON/OFF 토글"""
        # 모드가 꺼져 있으면 LOCK은 의미가 없음
        if not self.mode_on:
            return
        self.locked = not self.locked

    @abc.abstractmethod
    def process(self, hand_tracker, frame):
        """
        매 프레임마다 호출됨.
        - hand_tracker: HandTracker 인스턴스(현재 프레임의 손 랜드마크 결과 포함)
        - frame: OpenCV로 가져온 BGR 프레임 (반전된 상태)

        - 모드가 꺼져 있거나 LOCK이 걸려 있으면 내부에서 바로 False 반환
        - True : “실제로 상태(볼륨, 마우스 등)가 변경되었을 때”  
        - False: 변경이 없었을 때
        """
        pass

    @abc.abstractmethod
    def display_info(self, frame):
        """
        각 컨트롤러가 화면에 그려야 할 UI 정보를 그려주는 메서드.
        예) Mode/Lock 상태, 현재 볼륨 퍼센트, 마우스 커서 상태 등.
        - frame: OpenCV BGR 프레임 (반전된 상태)
        """
        pass
