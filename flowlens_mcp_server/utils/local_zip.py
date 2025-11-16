import json

import aiofiles
from ..dto import dto, dto_timeline
from ..models import enums
import zipfile
import asyncio
from pathlib import Path

class LocalZipClient:
    def __init__(self, zip_file_path: str):
        self.zip_file_path = zip_file_path
        self._extracted_path = None
        self._timeline_filename = 'timeline.json'
        self._video_filename = 'video.webm'
        self._rrweb_filename = 'rrweb_video.json'
        
    async def get(self) -> dto.FullFlow:
        self._extracted_path = await self._extract_zip()
        flow = await self._load_flow_from_timeline_json()
        local_files_data = self._create_local_files_data()
        flow.local_files_data = local_files_data
        return flow
    
    async def _load_flow_from_timeline_json(self) -> dto.FullFlow:
        timeline_file_path = self._extracted_path / self._timeline_filename
        async with aiofiles.open(timeline_file_path, mode='r') as f:
            content = await f.read()
        timeline_json = json.loads(content)
        flow_dict = timeline_json.get('metadata').get('flow')
        flow_dict['is_local'] = True
        flow = dto.FullFlow.model_validate(flow_dict)
        return flow
    
    def _create_local_files_data(self) -> dto.LocalFilesData:
        timeline_file_path = self._extracted_path / self._timeline_filename
        video_file_path = None
        rrweb_file_path = None
        
        video_file_path = self._extracted_path / self._video_filename
        rrweb_file_path = self._extracted_path / self._rrweb_filename
        
        return dto.LocalFilesData(
            zip_file_path=self.zip_file_path,
            extracted_dir_path=str(self._extracted_path),
            timeline_file_path=str(timeline_file_path),
            video_file_path=str(video_file_path),
            rrweb_file_path=str(rrweb_file_path)
        )
    
    async def _extract_zip(self) -> Path:
        extract_path = Path(self.zip_file_path).parent / Path(self.zip_file_path).stem
        await asyncio.to_thread(self._extract_zip_sync, extract_path)
        return extract_path

    def _extract_zip_sync(self, extract_path: Path):
        with zipfile.ZipFile(self.zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
