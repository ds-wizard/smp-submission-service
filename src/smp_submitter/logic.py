import asyncio
import base64
import datetime
import logging

import httpx
import rdflib


from .config import Config

GH_API = 'https://api.github.com'
LOG = logging.getLogger(__name__)


async def process(content: str, content_type: str) -> str:
    LOG.debug('Getting GitHub repo name')
    repo_name = get_github_reponame(content, content_type)
    LOG.debug(f'GitHub repo name: {repo_name}')
    try:
        return await create_fork_pr(repo_name, content)
    except Exception as e:
        raise RuntimeError(f'Failed to create a fork and submit PR:\n\n{str(e)}')


async def create_fork_pr(repo_name: str, content: str) -> str:
    LOG.debug('Creating a fork and submitting PR to the original repo')
    headers = {
        'Accept': 'application/vnd.github+json',
        'Authorization': f'Bearer {Config.GITHUB_TOKEN}',
        'X-GitHub-Api-Version': '2022-11-28',
    }
    async with httpx.AsyncClient(headers=headers) as client:
        # create a fork with branch based on UUID
        timestamp = datetime.datetime.now().strftime(f'%Y%m%d-%H%M%S')
        fork_name = f'{repo_name.replace("/", "-")}-{timestamp}'
        LOG.debug(f'Creating a fork: {fork_name} from {repo_name} repo')
        r = await client.post(
            url=f'{GH_API}/repos/{repo_name}/forks',
            json={
                'name': fork_name,
                'default_branch_only': True,
            },
        )
        r.raise_for_status()
        fork_repo_name = r.json()['full_name']
        username = r.json()['owner']['login']
        branch = r.json()['default_branch']

        # wait till fork is created (async)
        await asyncio.sleep(2)
        while True:
            r = await client.get(
                url=f'{GH_API}/repos/{fork_repo_name}',
            )
            if r.status_code != 404:
                r.raise_for_status()
                break
            await asyncio.sleep(5)
        LOG.debug(f'Fork created: {fork_repo_name} with default branch: {branch} by {username}')

        # submit the file there via GitHub API
        LOG.debug(f'Creating metadata.json in {fork_repo_name} repo.')
        r = await client.put(
            url=f'{GH_API}/repos/{fork_repo_name}/contents/metadata.json',
            json={
                'content': base64.b64encode(content.encode('utf-8')).decode('ascii'),
                'name': Config.GITHUB_NAME,
                'email': Config.GITHUB_EMAIL,
                'message': 'Update metadata from maSMP',
            },
        )
        r.raise_for_status()

        # create a PR via GitHub API
        LOG.debug(f'Creating a PR from {username}:{branch} to {repo_name}:{branch}')
        r = await client.post(
            url=f'{GH_API}/repos/{repo_name}/pulls',
            json={
                'title': 'Update metadata from maSMP',
                'body': 'Hey! This metadata has been submitted from the Software Management Wizard via maSMP.',
                'head': f'{username}:{branch}',
                'head_repo': fork_repo_name,
                'base': branch,
                'maintainer_can_modify': True,
            }
        )
        r.raise_for_status()
        pr_url = r.json()['html_url']
        LOG.debug(f'PR created: {pr_url}')
        return pr_url


def get_github_reponame(content: str, content_type: str) -> str:
    g = create_rdf_graph(content, content_type)
    repos = g.objects(
        predicate=rdflib.URIRef('https://schema.org/codeRepository'),
        unique=True,
    )
    for repo in repos:
        repo = str(repo)
        if not repo.startswith('https://github.com/'):
            continue
        repo = repo[19:]
        if repo.count('/') != 1:
            continue
        return repo
    raise RuntimeError('No valid GitHub repo found as schema:codeRepository')


def create_rdf_graph(content: str, content_type: str) -> rdflib.Graph:
    context = {
        '@context': {
            'schema': 'https://schema.org/',
        }
    }
    rdf_format = None
    if content_type == 'application/ld+json':
        rdf_format = 'json-ld'
    else:
        rdf_format = 'json-ld'

    g = rdflib.Graph()
    g.parse(data=content, format=rdf_format, context=context)
    return g
