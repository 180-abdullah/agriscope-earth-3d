from __future__ import annotations

from ..models import AnalysisRequest, AnalysisResponse, MissionId
from . import carbon, crop_stress, fire_heat, flood, irrigation, land_change


async def run_mission(request: AnalysisRequest) -> AnalysisResponse:
    handlers = {
        MissionId.FLOOD: flood.analyze,
        MissionId.CROP_STRESS: crop_stress.analyze,
        MissionId.LAND_CHANGE: land_change.analyze,
        MissionId.IRRIGATION: irrigation.analyze,
        MissionId.CARBON: carbon.analyze,
        MissionId.FIRE_HEAT: fire_heat.analyze,
    }
    return await handlers[request.mission](request)
