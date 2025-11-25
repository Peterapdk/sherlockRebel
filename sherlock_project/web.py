import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sherlock_project.sherlock import sherlock
from sherlock_project.sites import SitesInformation
from sherlock_project.notify import QueryNotify
from sherlock_project.result import QueryResult, QueryStatus

app = FastAPI()
pool = ThreadPoolExecutor()

# Mount the static directory to serve static files
app.mount("/static", StaticFiles(directory="sherlock_project/static"), name="static")

templates = Jinja2Templates(directory="sherlock_project/templates")

class WebQueryNotify(QueryNotify):
    def __init__(self):
        super().__init__()
        self.results = []

    def update(self, result: QueryResult):
        if result.status == QueryStatus.CLAIMED:
            self.results.append({
                "site_name": result.site_name,
                "url_user": result.site_url_user,
            })

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/", response_class=HTMLResponse)
async def search_username(request: Request, username: str = Form(...)):
    loop = asyncio.get_event_loop()

    # Create object with all information about sites we are aware of.
    sites = SitesInformation(os.path.join(os.path.dirname(__file__), "resources/data.json"))
    site_data_all = {site.name: site.information for site in sites}

    # Create notify object for query results.
    query_notify = WebQueryNotify()

    # Run report on the username in a separate thread
    await loop.run_in_executor(
        pool,
        sherlock,
        username,
        site_data_all,
        query_notify
    )

    return templates.TemplateResponse("index.html", {
        "request": request,
        "username": username,
        "results": query_notify.results,
    })
