import asyncio
import google.generativeai as genai
import time
from local_mcp_server.utils.settings import settings


class VideoSummarizer:
    def __init__(self, flow_id: str):
        self.flow_id = flow_id
        self.video_path = f"{settings.save_dir_path}/flows/{self.flow_id}/video.webm"
        genai.configure(api_key=settings.google_api_key)
        
    async def summarize(self) -> str:
        return await asyncio.to_thread(self._summarize_with_genai)
    
    def _summarize_with_genai(self) -> str:
        video_file = genai.upload_file(path=self.video_path)
        while video_file.state.name == "PROCESSING":
            time.sleep(10)
            video_file = genai.get_file(video_file.name)

        if video_file.state.name == "FAILED":
            raise ValueError(video_file.state.name)
        model = genai.GenerativeModel(model_name="gemini-2.5-pro")

        # Create the prompt, including the uploaded file
        prompt = """Summarize this video. Provide a timestamp in seconds for each key event in a single line. one line per event.
        The video is for a QA engineer testing a website. The video shows that there is something wrong in the website behavior e.g. a bug or a performance issue.
        Look carefully for any inconsistenciencies e.g. user did a change but the change didn't reflect on the UI.
        """

        response = model.generate_content([prompt, video_file])

        return response.text