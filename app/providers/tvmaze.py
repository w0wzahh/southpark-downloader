from __future__ import annotations
import re
import httpx
from app.models.entities import Episode, Season


class TVMazeProvider:
    BASE="https://api.tvmaze.com"
    SOUTH_PARK_ID=112

    def __init__(self):
        self.client=httpx.Client(timeout=20,follow_redirects=True)

    def fetch(self):
        show=self.client.get(f"{self.BASE}/shows/{self.SOUTH_PARK_ID}").raise_for_status()
        show=show.json()
        response=self.client.get(
            f"{self.BASE}/shows/{self.SOUTH_PARK_ID}/episodes?specials=0")
        response.raise_for_status()
        grouped={}
        for x in response.json():
            if x.get("number") is not None:
                grouped.setdefault(int(x["season"]),[]).append(x)
        seasons=[]
        episodes=[]
        for no in sorted(grouped):
            seasons.append(Season(no,f"Season {no}",len(grouped[no]),0))
            for x in sorted(grouped[no],key=lambda y:y["number"]):
                summary=re.sub("<[^>]+>","",x.get("summary") or "").strip()
                image=(x.get("image") or {}).get("original") or ""
                episodes.append(Episode(None,no,int(x["number"]),x.get("name") or "Untitled",
                    extension="mp4",airdate=x.get("airdate") or "",
                    runtime=x.get("runtime"),summary=summary,image_url=image))
        return show,seasons,episodes

    def close(self):
        self.client.close()
