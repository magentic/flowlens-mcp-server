import unittest
from datetime import datetime, timedelta, timezone
from local_mcp_server.utils.timeline.processor import TimelineProcessor
from local_mcp_server.dto import dto, dto_timeline

class TestTimelineProcessor(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        url = "https://storage.googleapis.com/flowlens-public/14/timeline.json?X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Credential=flowlens-be%40dev01-459220.iam.gserviceaccount.com%2F20251005%2Fauto%2Fstorage%2Fgoog4_request&X-Goog-Date=20251005T101506Z&X-Goog-Expires=86400&X-Goog-SignedHeaders=host&X-Goog-Signature=beacf5bebe772b3663b2710ac80d11c64fef60daa8ad0b5d314722b95df2a83199fef9b3dd787f26e68a56511e167b4f57dec857db90a69d02a59da7572bb7fcc6a4868ccba540666761ac1520a2a4dfabe6720b2cc134d4dcd5390b47d3a81d7edae467cfe39abb30cccba2b14866f4cd553363752a1c3af6f4cd15af68ff824cafc277e6046c3bd27e71f356001790736200917fddb9dad04ed0848eac28faf769d3ecc35d8cb687b160acc5564f6f122946a02c53ee16c2cc1e185fb2810e9fe722491feef8a0f53d08cc3b110e5d25a1ff288695370bc214ec217f10c7cdafabf6fa5c423334b1769b6431f0fad04b9aafaf989b5affe4ad84917fe88670"
        self._processor = TimelineProcessor(url)
        return super().setUp()
    
    async def test_process_timeline(self):
        overview = await self._processor.process()
        print(f"Timeline Overview: \n{overview}")
        # print(overview.timeline.create_events_summary())
        self.assertIsInstance(overview, dto_timeline.TimelineOverview)
    

if __name__ == "__main__":
    unittest.main()