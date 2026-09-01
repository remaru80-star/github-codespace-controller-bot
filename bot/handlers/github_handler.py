"""
GitHub API integration handlers
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from github_api.github_manager import GitHubManager
from database.db import db

logger = logging.getLogger(__name__)


async def set_github_repo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle setting GitHub repository"""
    query = update.callback_query
    await query.answer()
    
    app_id = query.data.split('_')[2]
    context.user_data['current_app_id'] = app_id
    context.user_data['action'] = 'set_repo'
    
    await query.edit_message_text(
        text="🔗 **Set GitHub Repository**\n\nEnter the GitHub repository URL:\n(e.g., https://github.com/username/repository)"
    )


async def set_env_vars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle setting environment variables"""
    query = update.callback_query
    await query.answer()
    
    app_id = query.data.split('_')[2]
    context.user_data['current_app_id'] = app_id
    context.user_data['action'] = 'set_env_vars'
    
    env_vars_text = """🌍 **Set Environment Variables**

Enter environment variables (one per line):
Format: KEY=value
Example:
NODE_ENV=production
DATABASE_URL=mongodb://..."""
    
    await query.edit_message_text(text=env_vars_text)


async def set_build_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle setting build command"""
    query = update.callback_query
    await query.answer()
    
    app_id = query.data.split('_')[2]
    context.user_data['current_app_id'] = app_id
    context.user_data['action'] = 'set_build_cmd'
    
    await query.edit_message_text(
        text="🔨 **Set Build Command**\n\nEnter the command to build your application:\nExample: npm install && npm run build"
    )


async def set_start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle setting start command"""
    query = update.callback_query
    await query.answer()
    
    app_id = query.data.split('_')[2]
    context.user_data['current_app_id'] = app_id
    context.user_data['action'] = 'set_start_cmd'
    
    await query.edit_message_text(
        text="▶️ **Set Start Command**\n\nEnter the command to start your application:\nExample: npm start or python app.py"
    )


async def set_docker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Docker implementation choice"""
    query = update.callback_query
    await query.answer()
    
    app_id = query.data.split('_')[2]
    
    keyboard = [
        [InlineKeyboardButton("✅ Yes (Use Docker)", callback_data=f"docker_yes_{app_id}")],
        [InlineKeyboardButton("❌ No (No Docker)", callback_data=f"docker_no_{app_id}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="🐳 **Docker Implementation**\n\nDo you want to use Docker for your application?",
        reply_markup=reply_markup
    )


async def handle_docker_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Docker choice selection"""
    query = update.callback_query
    await query.answer()
    
    choice = query.data.split('_')[1]
    app_id = query.data.split('_')[2]
    
    docker_enabled = (choice == 'yes')
    await db.update_application(app_id, {'docker_enabled': docker_enabled})
    
    status_text = "🐳 Docker: Enabled" if docker_enabled else "❌ Docker: Disabled"
    
    # Show configuration menu after Docker choice
    app = await db.get_application(app_id)
    config_text = f"⚙️ **{app['name']} Configuration**\n\n"
    config_text += f"✅ {status_text}\n\n"
    config_text += f"Repository: {app.get('repo_url', '❌ Not set')}\n"
    config_text += f"Env Vars: {'✅ ' + str(len(app.get('env_vars', {}))) + ' set' if app.get('env_vars') else '❌ Not set'}\n"
    config_text += f"Build Cmd: {'✅ Set' if app.get('build_command') else '❌ Not set'}\n"
    config_text += f"Start Cmd: {'✅ Set' if app.get('start_command') else '❌ Not set'}\n"
    config_text += f"Docker: {'🐳 Enabled' if app.get('docker_enabled') else '❌ Disabled'}\n\n"
    
    keyboard = [
        [InlineKeyboardButton("🔗 Set Repository", callback_data=f"set_repo_{app_id}")],
        [InlineKeyboardButton("🌍 Set Environment Variables", callback_data=f"set_env_{app_id}")],
        [InlineKeyboardButton("🔨 Set Build Command", callback_data=f"set_build_{app_id}")],
        [InlineKeyboardButton("▶️ Set Start Command", callback_data=f"set_start_{app_id}")],
        [InlineKeyboardButton("🐳 Docker Implementation", callback_data=f"set_docker_{app_id}")],
        [InlineKeyboardButton("✅ Review & Start", callback_data=f"review_{app_id}")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text=config_text, reply_markup=reply_markup)


async def fork_and_open_codespace(user_id: int, app_id: str, github_token: str):
    """Fork repository and open in Codespace"""
    try:
        app = await db.get_application(app_id)
        repo_url = app.get('repo_url')
        
        if not repo_url:
            return False, "Repository not configured"
        
        # Initialize GitHub manager
        gh_manager = GitHubManager(github_token)
        
        # Extract owner and repo from URL
        parts = repo_url.split('/')
        owner, repo = parts[-2], parts[-1].replace('.git', '')
        
        # Fork the repository
        forked_repo = await gh_manager.fork_repository(owner, repo)
        
        if not forked_repo:
            return False, "Failed to fork repository"
        
        # Create Codespace
        codespace = await gh_manager.create_codespace(
            forked_repo['full_name'],
            machine_type='standard_4_core_16gb_32gb'
        )
        
        if not codespace:
            return False, "Failed to create Codespace"
        
        # Update application with codespace info
        await db.update_application(app_id, {
            'forked_repo': forked_repo['full_name'],
            'codespace_id': codespace['id'],
            'codespace_name': codespace['name'],
            'status': 'running'
        })
        
        return True, {
            'codespace_url': codespace['web_url'],
            'codespace_name': codespace['name']
        }
    
    except Exception as e:
        logger.error(f"Error creating Codespace: {str(e)}")
        return False, str(e)
