"""
Settings and configuration handlers
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.db import db

logger = logging.getLogger(__name__)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show settings menu"""
    query = update.callback_query if update.callback_query else update
    
    keyboard = [
        [InlineKeyboardButton("🔑 Manage GitHub Tokens", callback_data="manage_tokens")],
        [InlineKeyboardButton("💳 View Billing", callback_data="view_billing")],
        [InlineKeyboardButton("📊 Usage Limits", callback_data="usage_limits")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    settings_text = """⚙️ **Settings**

Manage your bot settings and preferences:
- 🔑 Add and manage multiple GitHub tokens
- 💳 View your GitHub billing
- 📊 Set usage limits and alerts
    """
    
    if hasattr(query, 'edit_message_text'):
        await query.edit_message_text(text=settings_text, reply_markup=reply_markup)
    else:
        await query.message.reply_text(settings_text, reply_markup=reply_markup)


async def manage_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manage GitHub API tokens"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user = await db.get_user(user_id)
    tokens = user.get('github_tokens', [])
    
    if not tokens:
        keyboard = [
            [InlineKeyboardButton("➕ Add GitHub Token", callback_data="add_token")],
            [InlineKeyboardButton("⬅️ Back", callback_data="settings")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text="🔑 **GitHub Tokens**\n\nYou haven't added any GitHub API tokens yet.\n\nAdd your first token to get started controlling your Codespaces!",
            reply_markup=reply_markup
        )
        return
    
    tokens_text = "🔑 **Your GitHub Tokens**\n\n"
    buttons = []
    
    for i, token_info in enumerate(tokens, 1):
        token_preview = token_info['token'][:7] + '...' + token_info['token'][-4:] if token_info['token'] else 'Unknown'
        is_active = "✅ Active" if token_info.get('is_active') else "⭕ Inactive"
        added_date = token_info.get('added_at', 'Unknown').strftime('%d %b %Y') if hasattr(token_info.get('added_at'), 'strftime') else 'Unknown'
        
        tokens_text += f"**Token {i}:** `{token_preview}`\n"
        tokens_text += f"Status: {is_active}\n"
        tokens_text += f"Added: {added_date}\n\n"
        
        # Add buttons for each token
        if not token_info.get('is_active'):
            buttons.append([InlineKeyboardButton(
                f"✅ Use Token {i}",
                callback_data=f"switch_token_{token_info['_id']}"
            )])
        else:
            buttons.append([InlineKeyboardButton(
                f"✅ Token {i} (Active)",
                callback_data=f"token_info_{token_info['_id']}"
            )])
        
        buttons.append([InlineKeyboardButton(
            f"🗑️ Delete Token {i}",
            callback_data=f"delete_token_{token_info['_id']}"
        )])
    
    buttons.append([InlineKeyboardButton("➕ Add New Token", callback_data="add_token")])
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="settings")])
    
    reply_markup = InlineKeyboardMarkup(buttons)
    await query.edit_message_text(text=tokens_text, reply_markup=reply_markup)


async def add_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add new GitHub API token"""
    query = update.callback_query
    await query.answer()
    
    context.user_data['action'] = 'add_github_token'
    
    add_token_text = """🔑 **Add GitHub Personal Access Token**

Send your GitHub token below. To create one:

1. Go to: https://github.com/settings/tokens
2. Click "Generate new token"
3. Select scopes: `repo`, `codespace`
4. Copy the token and paste it here

**Token Format:** Should start with `ghp_` or `gho_`

Your token will be stored securely and only used to control your Codespaces.
    """
    
    await query.edit_message_text(text=add_token_text)


async def switch_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Switch active GitHub token"""
    query = update.callback_query
    await query.answer()
    
    token_id = query.data.split('_')[2]
    user_id = update.effective_user.id
    
    success = await db.switch_token(user_id, token_id)
    
    if success:
        await query.answer("✅ Token switched successfully!", show_alert=True)
        await manage_tokens(update, context)
    else:
        await query.answer("❌ Failed to switch token", show_alert=True)


async def delete_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete GitHub token"""
    query = update.callback_query
    await query.answer()
    
    token_id = query.data.split('_')[2]
    context.user_data['token_to_delete'] = token_id
    
    keyboard = [
        [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete_{token_id}")],
        [InlineKeyboardButton("❌ Cancel", callback_data="manage_tokens")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text="⚠️ **Confirm Delete**\n\nAre you sure you want to delete this GitHub token?\n\nYou will no longer be able to use this token for Codespace operations.",
        reply_markup=reply_markup
    )


async def confirm_delete_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm token deletion"""
    query = update.callback_query
    await query.answer()
    
    token_id = query.data.split('_')[2]
    user_id = update.effective_user.id
    
    success = await db.delete_token(user_id, token_id)
    
    if success:
        await query.edit_message_text(
            text="✅ **Token Deleted**\n\nThe GitHub token has been successfully deleted."
        )
        # Redirect back to manage tokens
        await manage_tokens(update, context)
    else:
        await query.answer("❌ Failed to delete token", show_alert=True)


async def view_billing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View GitHub billing information"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user = await db.get_user(user_id)
    
    if not user.get('github_tokens'):
        keyboard = [
            [InlineKeyboardButton("🔑 Add Token", callback_data="add_token")],
            [InlineKeyboardButton("⬅️ Back", callback_data="settings")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text="❌ **No GitHub Token**\n\nNo GitHub API token configured.\n\nAdd a token first to fetch billing information.",
            reply_markup=reply_markup
        )
        return
    
    billing_text = """💳 **GitHub Billing Information**

**Codespace Usage:**
- Hours Used: Calculating...
- Monthly Allowance: 120 hours
- Overage Rate: $0.18/hour

**Storage:**
- Used: Calculating...
- Included: 15 GB/month
- Overage Rate: $0.07/GB

**Note:** For detailed billing information and usage history, visit:
https://github.com/settings/billing/overview

**Tip:** Use `/settings` to manage multiple tokens and switch between them.
    """
    
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh", callback_data="view_billing")],
        [InlineKeyboardButton("⬅️ Back", callback_data="settings")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text=billing_text, reply_markup=reply_markup)


async def usage_limits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set usage limits and alerts"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("⏰ Set Codespace Limit", callback_data="set_codespace_limit")],
        [InlineKeyboardButton("💾 Set Storage Limit", callback_data="set_storage_limit")],
        [InlineKeyboardButton("🔔 Notifications", callback_data="notification_settings")],
        [InlineKeyboardButton("⬅️ Back", callback_data="settings")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    limits_text = """📊 **Usage Limits & Alerts**

Configure alerts and limits for your Codespace usage:

**Default Limits:**
- Monthly Codespace Hours: 120 hours
- Monthly Storage: 15 GB
- Auto-stop Idle: 30 minutes

Customize these limits to receive alerts before exceeding your GitHub billing allowance.
    """
    
    await query.edit_message_text(text=limits_text, reply_markup=reply_markup)


async def handle_token_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle GitHub token input from user"""
    user_id = update.effective_user.id
    token = update.message.text.strip()
    
    if context.user_data.get('action') == 'add_github_token':
        # Validate token format (GitHub tokens start with ghp_ or gho_)
        if not (token.startswith('ghp_') or token.startswith('gho_') or token.startswith('github_pat_')):
            keyboard = [
                [InlineKeyboardButton("🔄 Try Again", callback_data="add_token")],
                [InlineKeyboardButton("⬅️ Back", callback_data="manage_tokens")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                text="❌ **Invalid Token Format**\n\nGitHub tokens should start with:\n- `ghp_` (Personal Access Token)\n- `gho_` (OAuth token)\n- `github_pat_` (Fine-grained token)\n\nPlease check your token and try again.",
                reply_markup=reply_markup
            )
            return
        
        # Validate token length
        if len(token) < 20:
            await update.message.reply_text(
                text="❌ **Token Too Short**\n\nGitHub tokens are typically 40+ characters long. Please check your token."
            )
            return
        
        # Add token to user
        success = await db.add_github_token(user_id, token)
        context.user_data['action'] = None
        
        if success:
            keyboard = [
                [InlineKeyboardButton("✅ View All Tokens", callback_data="manage_tokens")],
                [InlineKeyboardButton("📱 My Applications", callback_data="my_apps")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                text="✅ **GitHub Token Added Successfully!**\n\nYour token is now active and ready to use for controlling Codespaces.\n\n🎉 You can now:\n- Create applications\n- Launch Codespaces\n- Manage your development environments",
                reply_markup=reply_markup
            )
        else:
            keyboard = [
                [InlineKeyboardButton("🔄 Try Again", callback_data="add_token")],
                [InlineKeyboardButton("⬅️ Back", callback_data="manage_tokens")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                text="❌ **Failed to Add Token**\n\nSomething went wrong. Please try again.",
                reply_markup=reply_markup
            )
