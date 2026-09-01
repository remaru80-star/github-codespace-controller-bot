"""GitHub API integration"""
import logging
from typing import Optional, Dict, Any
from github import Github, GithubException
from github import InputGitAuthor
import asyncio

logger = logging.getLogger(__name__)

# Bot's internal size labels -> real GitHub Codespaces machine identifiers.
# GitHub rejects the create call outright if "machine" isn't one of these
# (or isn't offered for that repo) - sending 'medium' / 'standard_4_core_16gb_32gb'
# like this code used to do always failed.
MACHINE_TYPE_MAP = {
    'small': 'basicLinux32gb',
    'medium': 'standardLinux32gb',
    'large': 'premiumLinux',
    'xlarge': 'largePremiumLinux',
}


class GitHubManager:
    """GitHub API manager for handling Codespace operations"""
    
    def __init__(self, token: str):
        """Initialize GitHub manager with token"""
        self.github = Github(token)
        self.token = token
    
    async def fork_repository(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """Fork a GitHub repository"""
        try:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self._sync_fork_repository, 
                owner, 
                repo
            )
            return result
        except Exception as e:
            logger.error(f"Error forking repository: {str(e)}")
            return None
    
    def _sync_fork_repository(self, owner: str, repo: str) -> Optional[Dict[str, Any]]:
        """Synchronous fork repository operation"""
        try:
            # Get the repository
            repo_obj = self.github.get_user(owner).get_repo(repo)
            
            # Check if already forked
            user = self.github.get_user()
            try:
                existing_fork = user.get_repo(repo)
                logger.info(f"Repository already forked: {existing_fork.full_name}")
                return {
                    'full_name': existing_fork.full_name,
                    'html_url': existing_fork.html_url,
                    'id': existing_fork.id,
                    'name': existing_fork.name
                }
            except GithubException:
                # Fork doesn't exist, create it
                forked_repo = user.create_fork(repo_obj)
                logger.info(f"Repository forked successfully: {forked_repo.full_name}")
                return {
                    'full_name': forked_repo.full_name,
                    'html_url': forked_repo.html_url,
                    'id': forked_repo.id,
                    'name': forked_repo.name
                }
        
        except GithubException as e:
            logger.error(f"GitHub error forking repository: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error in fork repository: {str(e)}")
            return None
    
    async def create_codespace(self, repo_full_name: str, machine_type: str = 'medium') -> Optional[Dict[str, Any]]:
        """Create a Codespace for a repository"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._sync_create_codespace,
                repo_full_name,
                machine_type
            )
            return result
        except Exception as e:
            logger.error(f"Error creating Codespace: {str(e)}")
            return None
    
    async def get_available_machines(self, repo_full_name: str) -> list:
        """List machine types GitHub actually offers for this repo"""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._sync_get_available_machines, repo_full_name)
        except Exception as e:
            logger.error(f"Error listing machines: {str(e)}")
            return []

    def _sync_get_available_machines(self, repo_full_name: str) -> list:
        try:
            import requests

            headers = {
                'Accept': 'application/vnd.github+json',
                'Authorization': f'Bearer {self.token}',
                'X-GitHub-Api-Version': '2022-11-28'
            }
            url = f"https://api.github.com/repos/{repo_full_name}/codespaces/machines"
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                return [m['name'] for m in response.json().get('machines', [])]
            logger.error(f"Failed to list machines: {response.status_code} - {response.text}")
            return []
        except Exception as e:
            logger.error(f"Error in list machines: {str(e)}")
            return []

    def _sync_create_codespace(self, repo_full_name: str, machine_type: str) -> Optional[Dict[str, Any]]:
        """Synchronous create Codespace operation"""
        try:
            owner, repo = repo_full_name.split('/')
            repo_obj = self.github.get_user(owner).get_repo(repo)
            
            # Create Codespace via REST API (PyGithub doesn't fully support Codespaces yet)
            # Using direct HTTP request through PyGithub's requester
            import requests
            
            headers = {
                'Accept': 'application/vnd.github+json',
                'Authorization': f'Bearer {self.token}',
                'X-GitHub-Api-Version': '2022-11-28'
            }

            # Resolve our internal label ('small'/'medium'/...) to a real GitHub
            # machine id, then confirm GitHub actually offers it for this repo.
            # Fall back to whatever is available rather than sending a value
            # GitHub will reject.
            available = self._sync_get_available_machines(repo_full_name)
            resolved_machine = MACHINE_TYPE_MAP.get(machine_type, machine_type)
            if available and resolved_machine not in available:
                logger.info(f"Machine '{resolved_machine}' not offered for {repo_full_name}, "
                            f"available: {available}. Falling back to '{available[0]}'.")
                resolved_machine = available[0]

            data = {'branch': repo_obj.default_branch}
            if resolved_machine:
                data['machine'] = resolved_machine
            
            url = f"https://api.github.com/repos/{repo_full_name}/codespaces"
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code in [200, 201, 202]:
                codespace_data = response.json()
                logger.info(f"Codespace created: {codespace_data.get('name')}")
                return {
                    'id': codespace_data.get('id'),
                    'name': codespace_data.get('name'),
                    'state': codespace_data.get('state'),
                    'web_url': codespace_data.get('web_url'),
                    'repository': codespace_data.get('repository'),
                    'machine': codespace_data.get('machine'),
                    'created_at': codespace_data.get('created_at'),
                }
            else:
                logger.error(f"Failed to create Codespace: {response.status_code} - {response.text}")
                return None
        
        except Exception as e:
            logger.error(f"Error in create Codespace: {str(e)}")
            return None
    
    async def stop_codespace(self, repo_full_name: str, codespace_name: str) -> bool:
        """Stop a Codespace"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._sync_stop_codespace,
                repo_full_name,
                codespace_name
            )
            return result
        except Exception as e:
            logger.error(f"Error stopping Codespace: {str(e)}")
            return False
    
    def _sync_stop_codespace(self, repo_full_name: str, codespace_name: str) -> bool:
        """Synchronous stop Codespace operation"""
        try:
            import requests
            
            headers = {
                'Accept': 'application/vnd.github+json',
                'Authorization': f'Bearer {self.token}',
                'X-GitHub-Api-Version': '2022-11-28'
            }
            
            url = f"https://api.github.com/user/codespaces/{codespace_name}/stop"
            response = requests.post(url, headers=headers, timeout=30)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Codespace stopped: {codespace_name}")
                return True
            else:
                logger.error(f"Failed to stop Codespace: {response.status_code} - {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Error in stop Codespace: {str(e)}")
            return False
    
    async def get_codespace(self, repo_full_name: str, codespace_name: str) -> Optional[Dict[str, Any]]:
        """Get Codespace details"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._sync_get_codespace,
                codespace_name
            )
            return result
        except Exception as e:
            logger.error(f"Error getting Codespace: {str(e)}")
            return None
    
    def _sync_get_codespace(self, codespace_name: str) -> Optional[Dict[str, Any]]:
        """Synchronous get Codespace operation"""
        try:
            import requests
            
            headers = {
                'Accept': 'application/vnd.github+json',
                'Authorization': f'Bearer {self.token}',
                'X-GitHub-Api-Version': '2022-11-28'
            }
            
            url = f"https://api.github.com/user/codespaces/{codespace_name}"
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get Codespace: {response.status_code}")
                return None
        
        except Exception as e:
            logger.error(f"Error in get Codespace: {str(e)}")
            return None
    
    async def list_user_codespaces(self) -> list:
        """List all Codespaces for authenticated user"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._sync_list_codespaces
            )
            return result
        except Exception as e:
            logger.error(f"Error listing Codespaces: {str(e)}")
            return []
    
    def _sync_list_codespaces(self) -> list:
        """Synchronous list Codespaces operation"""
        try:
            import requests
            
            headers = {
                'Accept': 'application/vnd.github+json',
                'Authorization': f'Bearer {self.token}',
                'X-GitHub-Api-Version': '2022-11-28'
            }
            
            url = "https://api.github.com/user/codespaces"
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('codespaces', [])
            else:
                logger.error(f"Failed to list Codespaces: {response.status_code}")
                return []
        
        except Exception as e:
            logger.error(f"Error in list Codespaces: {str(e)}")
            return []
    
    async def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get authenticated user information"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._sync_get_user_info)
            return result
        except Exception as e:
            logger.error(f"Error getting user info: {str(e)}")
            return None
    
    def _sync_get_user_info(self) -> Optional[Dict[str, Any]]:
        """Synchronous get user info"""
        try:
            user = self.github.get_user()
            return {
                'login': user.login,
                'name': user.name,
                'bio': user.bio,
                'public_repos': user.public_repos,
                'followers': user.followers,
            }
        except Exception as e:
            logger.error(f"Error in get user info: {str(e)}")
            return None
