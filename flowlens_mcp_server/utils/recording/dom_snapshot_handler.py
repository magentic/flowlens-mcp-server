import os
import json
import aiofiles
from ..settings import settings
from ...dto import dto

class DomSnapshotHandler:
    def __init__(self, flow: dto.FlowlensFlow):
        self._flow = flow
        if self._flow.is_local:
            self._rrweb_file_path = self._flow.local_files_data.rrweb_file_path
            self._snapshot_dir = f"{self._flow.local_files_data.extracted_dir_path}/snapshots"
        else:
            flow_dir = f"{settings.flowlens_save_dir_path}/flows/{self._flow.uuid}"
            self._rrweb_file_path = f"{flow_dir}/rrweb_video.json"
            self._snapshot_dir = f"{flow_dir}/snapshots"
        os.makedirs(self._snapshot_dir, exist_ok=True)
            
        
    async def save_snapshot(self, second: int) -> str:
        target_ms = second * 1000
        events = await self._extract_events()
        target_events = []
        for event in reversed(events):
            event_timestamp = event['timestamp']
            event_ms = (event_timestamp - events[0]['timestamp'])
            if event_ms > target_ms:
                continue
            if event['type'] == 2:
                target_events.append(event)
                break
            else:
                target_events.append(event)
                
        events_dict = {
            'rrwebEvents': list(reversed(target_events))
        }
            
        snapshot_path = f"{self._snapshot_dir}/snapshot_sec{second}.json"
        async with aiofiles.open(snapshot_path, mode='w') as f:
            await f.write(json.dumps(events_dict, indent=2))
        return snapshot_path
            
    async def _extract_events(self):
        if not os.path.exists(self._rrweb_file_path):
            raise FileNotFoundError(f"RRWEB file not found at {self._rrweb_file_path}")
        async with aiofiles.open(self._rrweb_file_path, mode='r') as f:
            content = await f.read()
        rrweb_events = json.loads(content)['rrwebEvents']
        return rrweb_events
