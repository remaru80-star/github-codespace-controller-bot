"""
Start command and initial setup handlers
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.models import User, Application
from database.db import db

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command - show main menu"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    # Ensure user exists in database
    await db.create_or_get_user(user_id, user_name)
    
    keyboard = [
        [InlineKeyboardButton("✨ Create New App", callback_data="create_app")],
        [InlineKeyboardButton("📱 My Applications", callback_data="my_apps")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        [InlineKeyboardButton("❓ Help", callback_data="help_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
🚀 Welcome to GitHub Codespace Controller Bot, {user_name}!

Control your GitHub Codespaces directly from Telegram. Create, manage, and deploy applications with ease.

**Quick Features:**
✅ Create Codespaces from any public GitHub repo
✅ Manage multiple GitHub API tokens
✅ Set custom build and start commands
✅ Docker and non-Docker deployment
✅ Monitor billing and usage
✅ Start/Stop Codespaces instantly

What would you like to do?
    """
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command and help_menu callback"""
    help_text = """
📖 **Help - Available Commands**

/start - Show main menu
/myapps - List your applications
/settings - Manage settings
/help - Show this help message

**Creating an Application:**
1. Click "Create New App"
2. Enter app name
3. Set GitHub repository URL
4. Configure environment variables (optional)
5. Set build commands (optional)
6. Set start commands (optional)
7. Choose Docker mode (yes/no)
8. Review and start

**Managing Codespaces:**
- Start Codespace: Creates and launches a new Codespace
- Stop Codespace: Gracefully stops running Codespace
- Check Status: View current Codespace status

**Codespace Specs (Default):**
- CPU: 4-Core
- RAM: 16GB
- Storage: 32GB

**Available Machine Types:**
- Small: 2-Core, 8GB RAM, 32GB Storage
- Medium: 4-Core, 16GB RAM, 32GB Storage
- Large: 8-Core, 32GB RAM, 64GB Storage
- XLarge: 16-Core, 64GB RAM, 128GB Storage

For more information, visit: https://github.com/OneAvobeAll/github-codespace-controller-bot
    """
    
    # Handle both command and callback query
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text=help_text, reply_markup=reply_markup)
    else:
        await update.effective_message.reply_text(help_text)


async def list_apps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List user's applications - handles both command and callback"""
    user_id = update.effective_user.id
    
    # Handle callback query
    if update.callback_query:
        query = update.callback_query
        await query.answer()
    
    apps = await db.get_user_applications(user_id)
    
    if not apps:
        message = "📭 You haven't created any applications yet.\n\nUse /start to create your first app!"
        if update.callback_query:
            await update.callback_query.edit_message_text(message)
        else:
            await update.effective_message.reply_text(message)
        return
    
    app_list = "📱 **Your Applications:**\n\n"
    buttons = []
    
    for app in apps:
        app_list += f"• **{app['name']}**\n"
        app_list += f"  Repository: {app.get('repo_url', 'N/A')}\n"
        app_list += f"  Status: {app.get('status', 'inactive')}\n"
        app_list += f"  Docker: {'Yes' if app.get('docker_enabled') else 'No'}\n\n"
        
        buttons.append([
            InlineKeyboardButton(f"📋 {app['name']}", callback_data=f"app_details_{app['_id']}")
        ])
    
    buttons.append([InlineKeyboardButton("➕ Create New App", callback_data="create_app")])
    buttons.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    
    reply_markup = InlineKeyboardMarkup(buttons)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text=app_list, reply_markup=reply_markup)
    else:
        await update.effective_message.reply_text(app_list, reply_markup=reply_markup)


async def show_app_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed app configuration"""
    query = update.callback_query
    await query.answer()
    
    app_id = query.data.split('_')[2]
    context.user_data['current_app_id'] = app_id
    
    app = await db.get_application(app_id)
    
    config_text = f"⚙️ **{app['name']} Configuration**\n\n"
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
        [InlineKeyboardButton("📱 My Applications", callback_data="my_apps")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text=config_text, reply_markup=reply_markup)


async def handle_review_app(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Review & Start button"""
    query = update.callback_query
    await query.answer()
    
    app_id = query.data.split('_')[1]
    app = await db.get_application(app_id)
    
    # Validate configuration
    if not app.get('repo_url'):
        await query.edit_message_text(
            text="❌ **Configuration Incomplete**\n\nPlease set the GitHub repository URL before starting."
        )
        return
    
    # Show review summary
    review_text = f"""
✅ **Review Configuration**

**Application Name:** {app['name']}
**Repository:** {app.get('repo_url')}
**Environment Variables:** {len(app.get('env_vars', {}))} set
**Build Command:** {app.get('build_command', 'Not set')}
**Start Command:** {app.get('start_command', 'Not set')}
**Docker:** {'🐳 Enabled' if app.get('docker_enabled') else '❌ Disabled'}

Ready to launch Codespace? Click below to proceed.
    """
    
    keyboard = [
        [InlineKeyboardButton("🚀 Start Codespace", callback_data=f"start_codespace_{app_id}")],
        [InlineKeyboardButton("🔙 Back to Config", callback_data=f"app_details_{app_id}")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text=review_text, reply_markup=reply_markup)


async def handle_create_app(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle create app button click"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        text="📝 **Create New Application**\n\nPlease enter the name for your new application:"
    )
    
    # Set context for next message handler
    context.user_data['action'] = 'create_app'


async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user text input"""
    user_id = update.effective_user.id
    user_input = update.message.text
    
    if context.user_data.get('action') == 'create_app':
        await _process_app_name(update, context, user_id, user_input)
    elif context.user_data.get('action') == 'set_repo':
        await _process_repo_url(update, context, user_id, user_input)
    elif context.user_data.get('action') == 'set_env_vars':
        await _process_env_vars(update, context, user_id, user_input)
    elif context.user_data.get('action') == 'set_build_cmd':
        await _process_build_cmd(update, context, user_id, user_input)
    elif context.user_data.get('action') == 'set_start_cmd':
        await _process_start_cmd(update, context, user_id, user_input)


async def _process_app_name(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, app_name: str):
    """Process app name input"""
    # Create new app in database
    app_id = await db.create_application(user_id, app_name)
    context.user_data['current_app_id'] = app_id
    context.user_data['action'] = None
    
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
    
    await update.message.reply_text(
        f"✅ App **{app_name}** created!\n\nNow configure your application:",
        reply_markup=reply_markup
    )


async def _process_repo_url(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, repo_url: str):
    """Process repository URL input"""
    app_id = context.user_data.get('current_app_id')
    
    # Validate GitHub URL
    if not ('github.com' in repo_url):
        await update.message.reply_text(
            "❌ Invalid GitHub URL. Please provide a valid GitHub repository URL (e.g., https://github.com/user/repo)"
        )
        return
    
    await db.update_application(app_id, {'repo_url': repo_url})
    context.user_data['action'] = None
    
    await update.message.reply_text(f"✅ Repository set to: {repo_url}")
    await _show_app_menu(update, context, app_id)


async def _process_env_vars(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, env_vars: str):
    """Process environment variables input"""
    app_id = context.user_data.get('current_app_id')
    
    # Parse env vars (format: KEY=value, KEY2=value2)
    env_dict = {}
    try:
        for line in env_vars.split('\n'):
            if '=' in line:
                key, value = line.split('=', 1)
                env_dict[key.strip()] = value.strip()
    except Exception as e:
        await update.message.reply_text(f"❌ Error parsing environment variables: {str(e)}")
        return
    
    await db.update_application(app_id, {'env_vars': env_dict})
    context.user_data['action'] = None
    
    await update.message.reply_text(f"✅ Environment variables set ({len(env_dict)} variables)")
    await _show_app_menu(update, context, app_id)


async def _process_build_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, build_cmd: str):
    """Process build command input"""
    app_id = context.user_data.get('current_app_id')
    await db.update_application(app_id, {'build_command': build_cmd})
    context.user_data['action'] = None
    
    await update.message.reply_text(f"✅ Build command set: `{build_cmd}`")
    await _show_app_menu(update, context, app_id)


async def _process_start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, start_cmd: str):
    """Process start command input"""
    app_id = context.user_data.get('current_app_id')
    await db.update_application(app_id, {'start_command': start_cmd})
    context.user_data['action'] = None
    
    await update.message.reply_text(f"✅ Start command set: `{start_cmd}`")
    await _show_app_menu(update, context, app_id)


async def _show_app_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, app_id: str):
    """Show application configuration menu"""
    app = await db.get_application(app_id)
    
    config_text = f"⚙️ **{app['name']} Configuration**\n\n"
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
    
    await update.message.reply_text(config_text, reply_markup=reply_markup)


async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to main menu"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("✨ Create New App", callback_data="create_app")],
        [InlineKeyboardButton("📱 My Applications", callback_data="my_apps")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        [InlineKeyboardButton("❓ Help", callback_data="help_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="🏠 **Main Menu**\n\nWhat would you like to do?",
        reply_markup=reply_markup
    )
