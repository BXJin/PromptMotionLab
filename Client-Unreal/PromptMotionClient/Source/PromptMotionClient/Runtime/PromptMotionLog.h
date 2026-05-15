#pragma once

#include "Logging/LogMacros.h"

/**
 * PromptMotion 전용 로그 카테고리.
 *
 * UE Output Log 필터에서 "LogPromptMotion" 선택 시 모듈 로그만 표시됨.
 * 로그 파일 경로: Saved/Logs/PromptMotionClient.log
 *
 * Verbosity:
 *   Log     — 정상 흐름 (요청/응답/preset 적용)
 *   Warning — 복구 가능한 문제 (TargetMesh 없음, 서버 오류)
 *   Error   — 치명적 문제 (미사용, ensure로 대체)
 */
DECLARE_LOG_CATEGORY_EXTERN(LogPromptMotion, Log, All);
