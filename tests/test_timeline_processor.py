import unittest
from datetime import datetime, timedelta, timezone
from local_mcp_server.utils.timeline.processor import TimelineProcessor
from local_mcp_server.dto import dto, dto_timeline

class TestTimelineProcessor(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        url = "https://storage.googleapis.com/flowlens-public/14/timeline.json?X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Credential=flowlens-be%40dev01-459220.iam.gserviceaccount.com%2F20251006%2Fauto%2Fstorage%2Fgoog4_request&X-Goog-Date=20251006T145634Z&X-Goog-Expires=86400&X-Goog-SignedHeaders=host&X-Goog-Signature=232e98d29274196c85bbb2fc5925e2287675495f83d6b3565486b06756c2172f8ed48eb8bed7bc3ca3ffb5c0d5342dde52d492ea176430c4f827bd42b795ac2500063d09c43f2bf37d0034661ca11455e327593340ba0a06e892afa5c04324e4945f679e26c8df4085e93fff2bef672c2ba54123a2d7aa2b41be6b51434173c87a632823c7928b4b5ada13f37f63b97e52f529ed01075aac34bd12508e790ada168cef42b4486a525d7ec993bfe1923edbc14e5cfce75f1c3061fa5b0a3739f21293123707f70241b38e038ee89d8a5a36916814df3afec5051223f20d93e4edf0793ac09efb764dbf29575d3adc0a0fa8caee6db10af6e955c4b787893de08e"
        self._processor = TimelineProcessor(url)
        return super().setUp()
    
    async def test_process_timeline(self):
        overview = await self._processor.process()
        # print(f"Timeline Overview: \n{overview}")
        # print(overview.timeline.create_events_summary())
        # res = overview.timeline.search_events_with_regex("status_code=400", dto.enums.TimelineEventType.NETWORK_REQUEST_WITH_RESPONSE)
        # res = overview.timeline.create_event_summary_for_range(0, 1000, dto.enums.TimelineEventType.NETWORK_REQUEST_WITH_RESPONSE)
        res = overview.timeline.get_full_event_by_index(464)
        res = res.search_with_regex("status_code=400")
        print(res)
        self.assertIsInstance(overview, dto_timeline.TimelineOverview)
    

if __name__ == "__main__":
    unittest.main()