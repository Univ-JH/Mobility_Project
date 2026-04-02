# 하드웨어 없이 로직만 테스트하는 코드
def mock_decision(h_worn, h_fall, dist, road):
    # 우리가 짠 5번 파일의 if-elif 로직 그대로!
    if not h_worn: return "EMERGENCY (사유: 헬멧 미착용)"
    elif h_fall: return "EMERGENCY (사유: 사고 발생)"
    elif dist < 1.0: return "BRAKE (사유: 장애물 근접)"
    elif road == "SIDEWALK": return "LIMIT (사유: 인도 주행)"
    else: return "RELEASE (사유: 정상 도로)"

# 시뮬레이션 돌려보기
print("1. 인도에서 장애물 발견:", mock_decision(True, False, 0.7, "SIDEWALK"))
print("2. 도로에서 헬멧 벗음:", mock_decision(False, False, 5.0, "ROAD"))
print("3. 인도에서 정상 주행:", mock_decision(True, False, 3.0, "SIDEWALK"))