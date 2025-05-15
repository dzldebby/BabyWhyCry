import logging
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    CallbackQueryHandler, ConversationHandler, ContextTypes
)
from sqlalchemy.orm import Session

from database import SessionLocal, get_recent_events, get_baby_stats
from database import create_user, create_baby, start_feeding, end_feeding, start_sleep, end_sleep, log_diaper_change, start_crying, end_crying
from database import get_last_feeding, get_last_sleep, get_last_diaper, get_last_crying
from database import get_feeding_count, get_sleep_duration, get_diaper_count, get_crying_episodes, get_baby_schedule
from models import User, Baby, Feeding, FeedingType, DiaperType, CryingReason
from predictor import predict_crying_reason, analyze_crying_episode
from nlp_handler import process_query, generate_response, parse_time_period
from utils import format_datetime, utc_to_sgt, get_sgt_now


# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
(SELECT_BABY, MAIN_MENU, FEEDING, FEEDING_TYPE, FEEDING_AMOUNT, 
 SLEEP, DIAPER, DIAPER_TYPE, CRYING, CRYING_REASON, 
 HISTORY, STATS, SETTINGS, ADD_BABY, NATURAL_LANGUAGE_QUERY,
 CHANGE_BABY_NAME) = range(16)

# Get a database session
def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

# Helper for keyboard markups
def get_baby_keyboard(user_id):
    db = get_db()
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return []
    
    keyboard = []
    for baby in user.babies:
        keyboard.append([InlineKeyboardButton(baby.name, callback_data=f"baby_{baby.id}")])
    
    keyboard.append([InlineKeyboardButton("➕ Add Baby", callback_data="add_baby")])
    return keyboard

def get_main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🍼 Feeding", callback_data="feeding"),
         InlineKeyboardButton("💤 Sleep", callback_data="sleep")],
        [InlineKeyboardButton("💩 Diaper", callback_data="diaper"),
         InlineKeyboardButton("👶 Crying", callback_data="crying")],
        [InlineKeyboardButton("📊 History", callback_data="history"),
         InlineKeyboardButton("📈 Stats", callback_data="stats")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
         InlineKeyboardButton("👋 Change Baby", callback_data="change_baby")]
    ]
    return keyboard

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start command handler, creates user if needed and shows baby selection."""
    user = update.effective_user
    db = get_db()
    
    # Check if user exists, create if not
    db_user = db.query(User).filter(User.username == user.username).first()
    if not db_user:
        db_user = create_user(db, user.username, f"{user.username}@telegram.org")
    
    context.user_data["user_id"] = db_user.id
    
    # Check for deep link parameter
    args = context.args
    deep_link = args[0] if args else None
    
    # Handle quick bottle feed deep link
    if deep_link == "quick_bottle":
        # Check if the user has babies first
        if db_user.babies:
            # If user has only one baby, auto-select it
            if len(db_user.babies) == 1:
                baby = db_user.babies[0]
                baby_id = baby.id
                context.user_data["baby_id"] = baby_id
                
                # Start a bottle feeding
                try:
                    feeding = start_feeding(db, baby_id, FeedingType.BOTTLE)
                    context.user_data["current_feeding_id"] = feeding.id
                    await update.message.reply_text(
                        f"✅ Quick bottle feeding started for {baby.name}!\n\n"
                        "I'll ask for the amount when you're done. To end the feeding, "
                        "tap the button below or send /done",
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("✅ Done Feeding", callback_data="done_feeding")]
                        ])
                    )
                    return FEEDING
                except Exception as e:
                    logger.error(f"Error starting quick bottle feeding: {e}")
                    await update.message.reply_text(
                        "Sorry, there was an error starting the feeding. Please try again."
                    )
                    return await menu_command(update, context)
            else:
                # If multiple babies, show a special baby selection for quick bottle
                keyboard = []
                for baby in db_user.babies:
                    keyboard.append([InlineKeyboardButton(f"🍼 {baby.name}", callback_data=f"quick_bottle_{baby.id}")])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "Please select which baby to start a bottle feeding for:",
                    reply_markup=reply_markup
                )
                return SELECT_BABY
        else:
            # No babies yet, prompt to add one
            await update.message.reply_text(
                "Welcome to Baby Alert! 👶\n\n"
                "Before using quick bottle feeding, you need to add a baby first. "
                "Please send me your baby's name."
            )
            return ADD_BABY
    # Handle the case when baby is already selected (for existing users)
    elif deep_link == "quick_bottle" and "baby_id" in context.user_data:
        baby_id = context.user_data["baby_id"]
        baby = db.query(Baby).filter(Baby.id == baby_id).first()
        
        if baby:
            # Start a bottle feeding
            try:
                feeding = start_feeding(db, baby_id, FeedingType.BOTTLE)
                context.user_data["current_feeding_id"] = feeding.id
                await update.message.reply_text(
                    f"✅ Quick bottle feeding started for {baby.name}!\n\n"
                    "I'll ask for the amount when you're done. To end the feeding, "
                    "tap the button below or send /done",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ Done Feeding", callback_data="done_feeding")]
                    ])
                )
                return FEEDING
            except Exception as e:
                logger.error(f"Error starting quick bottle feeding: {e}")
                await update.message.reply_text(
                    "Sorry, there was an error starting the feeding. Please try again."
                )
                return await menu_command(update, context)
    # Check if user has babies
    elif not db_user.babies:
        await update.message.reply_text(
            "Welcome to Baby Alert! 👶\n\n"
            "Looks like you don't have any babies registered yet. "
            "Let's add one now! Please send me your baby's name."
        )
        return ADD_BABY
    
    # Show baby selection
    keyboard = get_baby_keyboard(db_user.id)
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "Welcome to Baby Alert! 👶\n\n"
        "Please select a baby:",
        reply_markup=reply_markup
    )
    
    return SELECT_BABY

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_text = (
        "🤖 *Baby Alert Bot Commands*\n\n"
        "/start - Start the bot and select a baby\n"
        "/help - Show this help message\n"
        "/menu - Show the main menu\n"
        "/quick_bottle - Start a quick bottle feeding\n"
        "/done - End the current feeding session\n\n"
        "*What can this bot do?*\n"
        "- Track feedings (breast, bottle, solid)\n"
        "- Track sleep periods\n"
        "- Track diaper changes\n"
        "- Analyze crying episodes\n"
        "- Show history of events\n"
        "- Provide statistics and insights\n\n"
        "You can also ask me questions like:\n"
        "- When was the last feeding?\n"
        "- How long did the baby sleep today?\n"
        "- How many diapers were changed yesterday?\n\n"
        "Use the buttons to navigate and record baby events!"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def quick_bottle_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start a quick bottle feeding."""
    if "baby_id" not in context.user_data:
        await update.message.reply_text(
            "Please select a baby first using the /start command."
        )
        return await start(update, context)
    
    baby_id = context.user_data["baby_id"]
    db = get_db()
    baby = db.query(Baby).filter(Baby.id == baby_id).first()
    
    if not baby:
        await update.message.reply_text(
            "Sorry, I couldn't find your baby's information. Please select a baby first."
        )
        return await start(update, context)
    
    # Start a bottle feeding
    try:
        feeding = start_feeding(db, baby_id, FeedingType.BOTTLE)
        context.user_data["current_feeding_id"] = feeding.id
        await update.message.reply_text(
            f"✅ Quick bottle feeding started for {baby.name}!\n\n"
            "I'll ask for the amount when you're done. To end the feeding, "
            "tap the button below or send /done",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Done Feeding", callback_data="done_feeding")]
            ])
        )
        return FEEDING
    except Exception as e:
        logger.error(f"Error starting quick bottle feeding: {e}")
        await update.message.reply_text(
            "Sorry, there was an error starting the feeding. Please try again."
        )
        return await menu_command(update, context)

async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show the main menu."""
    if "baby_id" not in context.user_data:
        # If no baby is selected, show baby selection
        return await start(update, context)
    
    db = get_db()
    baby = db.query(Baby).filter(Baby.id == context.user_data["baby_id"]).first()
    
    reply_markup = InlineKeyboardMarkup(get_main_menu_keyboard())
    
    await update.message.reply_text(
        f"👶 *{baby.name}*\n\n"
        "What would you like to do?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return MAIN_MENU

# Natural language query handler
async def handle_natural_language_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process natural language queries from the user."""
    # Check if a baby is selected
    if "baby_id" not in context.user_data:
        await update.message.reply_text(
            "Please select a baby first using the /start command."
        )
        return await start(update, context)
    
    # Get the query text
    query_text = update.message.text
    baby_id = context.user_data["baby_id"]
    
    # Send typing action
    await update.message.chat.send_action('typing')
    
    # Process the query
    db_function, intent, parameters = process_query(query_text, baby_id)
    
    # Get the baby name
    db = get_db()
    baby = db.query(Baby).filter(Baby.id == baby_id).first()
    baby_name = baby.name if baby else "your baby"
    
    # Handle time period if present
    start_time = None
    end_time = None
    if "time_period" in parameters and parameters["time_period"]:
        start_time, end_time = parse_time_period(parameters["time_period"])
    
    # Call the appropriate database function based on intent
    data = {}
    if db_function == "get_last_feeding":
        data = get_last_feeding(db, baby_id)
    elif db_function == "get_last_sleep":
        data = get_last_sleep(db, baby_id)
    elif db_function == "get_last_diaper":
        data = get_last_diaper(db, baby_id)
    elif db_function == "get_last_crying":
        data = get_last_crying(db, baby_id)
    elif db_function == "get_feeding_count":
        data = get_feeding_count(db, baby_id, start_time, end_time)
    elif db_function == "get_sleep_duration":
        data = get_sleep_duration(db, baby_id, start_time, end_time)
    elif db_function == "get_diaper_count":
        data = get_diaper_count(db, baby_id, start_time, end_time)
    elif db_function == "get_crying_episodes":
        data = get_crying_episodes(db, baby_id, start_time, end_time)
    elif db_function == "get_baby_schedule":
        data = get_baby_schedule(db, baby_id)
    else:
        # Unknown intent
        await update.message.reply_text(
            f"I'm not sure how to answer that question about {baby_name}. "
            "You can ask about feedings, sleep, diapers, or crying episodes."
        )
        return NATURAL_LANGUAGE_QUERY
    
    # Add baby name to data for response generation
    data["baby_name"] = baby_name
    
    # Generate a natural language response
    response = generate_response(intent, data, query_text)
    
    # Send the response
    await update.message.reply_text(response)
    
    # Show a button to go back to the main menu
    keyboard = [[InlineKeyboardButton("↩️ Back to Menu", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "You can ask me another question or go back to the menu:",
        reply_markup=reply_markup
    )
    
    return NATURAL_LANGUAGE_QUERY

# Callback query handlers
async def baby_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle baby selection."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "add_baby":
        await query.edit_message_text(
            "Please send me your baby's name."
        )
        return ADD_BABY
    
    # Handle quick bottle feeding selection
    elif query.data.startswith("quick_bottle_"):
        baby_id = int(query.data.split('_')[2])
        context.user_data["baby_id"] = baby_id
        
        db = get_db()
        baby = db.query(Baby).filter(Baby.id == baby_id).first()
        
        # Start a bottle feeding
        try:
            feeding = start_feeding(db, baby_id, FeedingType.BOTTLE)
            context.user_data["current_feeding_id"] = feeding.id
            await query.edit_message_text(
                f"✅ Quick bottle feeding started for {baby.name}!\n\n"
                "I'll ask for the amount when you're done. To end the feeding, "
                "tap the button below or send /done",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Done Feeding", callback_data="done_feeding")]
                ])
            )
            return FEEDING
        except Exception as e:
            logger.error(f"Error starting quick bottle feeding: {e}")
            await query.edit_message_text(
                "Sorry, there was an error starting the feeding. Please try again."
            )
            reply_markup = InlineKeyboardMarkup(get_main_menu_keyboard())
            await query.edit_message_text(
                f"👶 *{baby.name}* selected!\n\n"
                "What would you like to do?",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            return MAIN_MENU
    
    # Normal baby selection
    else:
        baby_id = int(query.data.split('_')[1])
        context.user_data["baby_id"] = baby_id
        
        db = get_db()
        baby = db.query(Baby).filter(Baby.id == baby_id).first()
        
        reply_markup = InlineKeyboardMarkup(get_main_menu_keyboard())
        
        await query.edit_message_text(
            f"👶 *{baby.name}* selected!\n\n"
            "What would you like to do?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return MAIN_MENU

async def add_baby_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle adding a new baby."""
    name = update.message.text
    context.user_data["new_baby_name"] = name
    
    db = get_db()
    user_id = context.user_data["user_id"]
    
    # Create the baby
    baby = create_baby(db, name, user_id, birth_date=datetime.utcnow())
    context.user_data["baby_id"] = baby.id
    
    # Show main menu
    reply_markup = InlineKeyboardMarkup(get_main_menu_keyboard())
    
    await update.message.reply_text(
        f"👶 *{baby.name}* has been added!\n\n"
        "What would you like to do?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return MAIN_MENU

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle main menu selection."""
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    if action == "feeding":
        keyboard = [
            [InlineKeyboardButton("🤱 Breast", callback_data="feeding_breast"),
             InlineKeyboardButton("🍼 Bottle", callback_data="feeding_bottle")],
            [InlineKeyboardButton("🥄 Solid", callback_data="feeding_solid"),
             InlineKeyboardButton("↩️ Back", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "What type of feeding?",
            reply_markup=reply_markup
        )
        return FEEDING_TYPE
    
    elif action == "sleep":
        # Start sleep tracking
        db = get_db()
        baby_id = context.user_data["baby_id"]
        sleep = start_sleep(db, baby_id)
        context.user_data["sleep_id"] = sleep.id
        
        keyboard = [
            [InlineKeyboardButton("⏹️ End Sleep", callback_data="end_sleep")],
            [InlineKeyboardButton("↩️ Back to Menu", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"Sleep started at {format_datetime(sleep.start_time, include_seconds=True)}.\n"
            "Press 'End Sleep' when baby wakes up.",
            reply_markup=reply_markup
        )
        return SLEEP
    
    elif action == "diaper":
        keyboard = [
            [InlineKeyboardButton("💦 Wet", callback_data="diaper_wet"),
             InlineKeyboardButton("💩 Dirty", callback_data="diaper_dirty")],
            [InlineKeyboardButton("Both", callback_data="diaper_both"),
             InlineKeyboardButton("↩️ Back", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "What type of diaper change?",
            reply_markup=reply_markup
        )
        return DIAPER_TYPE
    
    elif action == "crying":
        # Start crying tracking and analyze
        db = get_db()
        baby_id = context.user_data["baby_id"]
        crying = start_crying(db, baby_id)
        context.user_data["crying_id"] = crying.id
        
        # Predict reason
        prediction = predict_crying_reason(db, baby_id)
        reason = prediction["predicted_reason"]
        confidence = prediction["confidence"]
        
        # Save prediction
        analyze_crying_episode(db, crying.id)
        
        # Custom message based on the predicted reason
        prediction_message = ""
        if reason == CryingReason.HUNGRY:
            prediction_message = f"Baby is probably hungry (confidence level: {confidence:.0f}%)"
        elif reason == CryingReason.DIAPER:
            prediction_message = f"Baby probably needs a change of diapers (confidence level: {confidence:.0f}%)"
        elif reason == CryingReason.ATTENTION:
            prediction_message = f"Baby probably just wants some attention (confidence level: {confidence:.0f}%)"
        else:
            prediction_message = f"Baby is probably {reason.value} (confidence level: {confidence:.0f}%)"
        
        keyboard = [
            [InlineKeyboardButton("🍼 Hungry", callback_data="reason_hungry"),
             InlineKeyboardButton("💩 Diaper", callback_data="reason_diaper")],
            [InlineKeyboardButton("🤗 Attention", callback_data="reason_attention"),
             InlineKeyboardButton("❓ Unknown", callback_data="reason_unknown")],
            [InlineKeyboardButton("↩️ Back to Menu", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"Crying episode started at {format_datetime(crying.start_time, include_seconds=True)}.\n\n"
            f"*Prediction*: {prediction_message}\n\n"
            "Please provide the actual reason when resolved:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return CRYING
    
    elif action == "history":
        db = get_db()
        baby_id = context.user_data["baby_id"]
        events = get_recent_events(db, baby_id, limit=5)
        
        text = "📝 *Recent Events*\n\n"
        
        for event in events:
            try:
                event_type = event["type"]
                event_time = format_datetime(event["time"], include_seconds=False)
                data = event["data"]
                
                if event_type == "feeding":
                    # Safely access type value, handling both enum and string
                    feeding_type = data.type
                    if hasattr(feeding_type, 'value'):
                        feeding_type_str = feeding_type.value
                    else:
                        feeding_type_str = str(feeding_type)
                    
                    text += f"🍼 *Feeding* ({feeding_type_str}) at {event_time}\n"
                    if data.end_time:
                        duration = (data.end_time - data.start_time).total_seconds() / 60
                        text += f"   Duration: {duration:.0f} minutes\n"
                    if data.amount:
                        text += f"   Amount: {data.amount} ml/oz\n"
                
                elif event_type == "sleep":
                    text += f"💤 *Sleep* started at {event_time}\n"
                    if data.end_time:
                        duration = (data.end_time - data.start_time).total_seconds() / 60
                        text += f"   Duration: {duration:.0f} minutes\n"
                
                elif event_type == "diaper":
                    # Safely access type value, handling both enum and string
                    diaper_type = data.type
                    if hasattr(diaper_type, 'value'):
                        diaper_type_str = diaper_type.value
                    else:
                        diaper_type_str = str(diaper_type)
                        
                    text += f"💩 *Diaper* ({diaper_type_str}) at {event_time}\n"
                
                elif event_type == "crying":
                    text += f"👶 *Crying* started at {event_time}\n"
                    if data.end_time:
                        duration = (data.end_time - data.start_time).total_seconds() / 60
                        text += f"   Duration: {duration:.0f} minutes\n"
                    if data.actual_reason:
                        # Safely access reason value, handling both enum and string
                        reason = data.actual_reason
                        if hasattr(reason, 'value'):
                            reason_str = reason.value
                        else:
                            reason_str = str(reason)
                        text += f"   Reason: {reason_str}\n"
                
                text += "\n"
            except Exception as e:
                logger.error(f"Error formatting event: {e}")
        
        keyboard = [
            [InlineKeyboardButton("↩️ Back to Menu", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return HISTORY
    
    elif action == "stats":
        db = get_db()
        baby_id = context.user_data["baby_id"]
        
        # Get stats for today
        today_stats = get_baby_stats(db, baby_id, days=1)
        
        # Get stats for week
        week_stats = get_baby_stats(db, baby_id, days=7)
        
        text = "📊 *Baby Stats*\n\n"
        text += "*Today:*\n"
        text += f"Feedings: {today_stats['feeding_count']}\n"
        text += f"Sleep: {today_stats['total_sleep_hours']:.1f} hours\n"
        text += f"Diapers: {today_stats['diaper_count']} ({today_stats['wet_diapers']} wet, {today_stats['dirty_diapers']} dirty, {today_stats['both_diapers']} both)\n\n"
        
        text += "*Past Week (Daily Average):*\n"
        text += f"Feedings: {week_stats['feeding_count']/7:.1f}\n"
        text += f"Sleep: {week_stats['total_sleep_hours']/7:.1f} hours\n"
        text += f"Diapers: {week_stats['diaper_count']/7:.1f}\n"
        
        keyboard = [
            [InlineKeyboardButton("↩️ Back to Menu", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return STATS
    
    elif action == "settings":
        keyboard = [
            [InlineKeyboardButton("👶 Add Another Baby", callback_data="add_baby")],
            [InlineKeyboardButton("✏️ Change Baby Name", callback_data="change_baby_name")],
            [InlineKeyboardButton("🗑️ Remove Baby Data", callback_data="remove_baby")],
            [InlineKeyboardButton("↩️ Back to Menu", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⚙️ *Settings*\n\n"
            "What would you like to do?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return SETTINGS
    
    elif action == "change_baby":
        # Show baby selection
        keyboard = get_baby_keyboard(context.user_data["user_id"])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "Please select a baby:",
            reply_markup=reply_markup
        )
        return SELECT_BABY
    
    elif action == "back_to_menu":
        # Show main menu
        reply_markup = InlineKeyboardMarkup(get_main_menu_keyboard())
        
        await query.edit_message_text(
            "What would you like to do?",
            reply_markup=reply_markup
        )
        return MAIN_MENU
    
    elif action == "remove_baby":
        # Show confirmation for baby removal
        baby_id = context.user_data["baby_id"]
        db = get_db()
        baby = db.query(Baby).filter(Baby.id == baby_id).first()
        
        keyboard = [
            [InlineKeyboardButton("✅ Yes, delete all data", callback_data="confirm_remove_baby")],
            [InlineKeyboardButton("❌ No, keep data", callback_data="back_to_settings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⚠️ *Warning*\n\n"
            f"Are you sure you want to delete all data for baby *{baby.name}*?\n\n"
            f"This will permanently remove all feeding, sleep, diaper, and crying records.\n"
            f"This action cannot be undone.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return SETTINGS
    
    elif action == "confirm_remove_baby":
        # Delete the baby and all related data
        baby_id = context.user_data["baby_id"]
        db = get_db()
        baby_name = db.query(Baby).filter(Baby.id == baby_id).first().name
        
        # Import the delete_baby function from database
        from database import delete_baby
        
        # Delete the baby
        success = delete_baby(db, baby_id)
        
        if success:
            # Remove baby_id from context
            del context.user_data["baby_id"]
            
            # Show success message
            await query.edit_message_text(
                f"✅ Successfully deleted all data for baby *{baby_name}*.",
                parse_mode='Markdown'
            )
            
            # Show baby selection if user has other babies
            user_id = context.user_data["user_id"]
            babies = db.query(Baby).filter(Baby.parent_id == user_id).all()
            
            if babies:
                # Show baby selection
                keyboard = get_baby_keyboard(user_id)
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    "Please select a baby:",
                    reply_markup=reply_markup
                )
                return SELECT_BABY
            else:
                # Prompt to add a new baby
                await query.edit_message_text(
                    "You have no babies registered. Please add a baby by sending the baby's name."
                )
                return ADD_BABY
        else:
            # Show error message
            keyboard = [
                [InlineKeyboardButton("↩️ Back to Settings", callback_data="back_to_settings")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "❌ Failed to delete baby data. Please try again later.",
                reply_markup=reply_markup
            )
            return SETTINGS
    
    elif action == "back_to_settings":
        # Go back to settings
        keyboard = [
            [InlineKeyboardButton("👶 Add Another Baby", callback_data="add_baby")],
            [InlineKeyboardButton("✏️ Change Baby Name", callback_data="change_baby_name")],
            [InlineKeyboardButton("🗑️ Remove Baby Data", callback_data="remove_baby")],
            [InlineKeyboardButton("↩️ Back to Menu", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "⚙️ *Settings*\n\n"
            "What would you like to do?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return SETTINGS
    
    elif action == "change_baby_name":
        # Get current baby info
        baby_id = context.user_data["baby_id"]
        db = get_db()
        baby = db.query(Baby).filter(Baby.id == baby_id).first()
        
        await query.edit_message_text(
            f"Current baby name: *{baby.name}*\n\n"
            "Please enter the new name for your baby:",
            parse_mode='Markdown'
        )
        return CHANGE_BABY_NAME
    
    return MAIN_MENU

async def feeding_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle feeding type selection."""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("feeding_"):
        feeding_type = query.data.split("_")[1]
        context.user_data["feeding_type"] = feeding_type
        
        if feeding_type == "breast":
            feeding_type_enum = FeedingType.BREAST
        elif feeding_type == "bottle":
            feeding_type_enum = FeedingType.BOTTLE
        elif feeding_type == "solid":
            feeding_type_enum = FeedingType.SOLID
        
        # Start feeding
        db = get_db()
        baby_id = context.user_data["baby_id"]
        feeding = start_feeding(db, baby_id, feeding_type_enum)
        context.user_data["feeding_id"] = feeding.id
        
        keyboard = []
        if feeding_type in ["bottle", "solid"]:
            keyboard.append([InlineKeyboardButton("➕ Add Amount", callback_data="add_amount")])
        
        keyboard.append([InlineKeyboardButton("⏹️ End Feeding", callback_data="end_feeding")])
        keyboard.append([InlineKeyboardButton("↩️ Back to Menu", callback_data="back_to_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"{feeding_type.capitalize()} feeding started at {format_datetime(feeding.start_time, include_seconds=True)}.\n"
            "Press 'End Feeding' when done.",
            reply_markup=reply_markup
        )
        return FEEDING
    
    elif query.data == "back_to_menu":
        # Back to main menu
        reply_markup = InlineKeyboardMarkup(get_main_menu_keyboard())
        
        await query.edit_message_text(
            "What would you like to do?",
            reply_markup=reply_markup
        )
        return MAIN_MENU
    
    return FEEDING_TYPE

async def feeding_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle feeding actions."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "add_amount":
        await query.edit_message_text(
            "Please enter the amount in ml or oz:"
        )
        return FEEDING_AMOUNT
    
    elif query.data == "end_feeding" or query.data == "done_feeding":
        db = get_db()
        feeding_id = context.user_data.get("feeding_id") or context.user_data.get("current_feeding_id")
        if not feeding_id:
            await query.edit_message_text(
                "Sorry, I couldn't find the current feeding session. Please try again.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("↩️ Back to Menu", callback_data="back_to_menu")]
                ])
            )
            return MAIN_MENU
            
        feeding = end_feeding(db, feeding_id)
        
        # Calculate duration
        duration = (feeding.end_time - feeding.start_time).total_seconds() / 60
        
        # Ask for amount if it's a bottle feeding and no amount recorded yet
        if feeding.type == FeedingType.BOTTLE and not feeding.amount:
            await query.edit_message_text(
                f"Bottle feeding ended at {format_datetime(feeding.end_time, include_seconds=True)}.\n"
                f"Duration: {duration:.0f} minutes.\n\n"
                f"Please enter the amount in ml or oz:",
            )
            return FEEDING_AMOUNT
        
        keyboard = [
            [InlineKeyboardButton("↩️ Back to Menu", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"Feeding ended at {format_datetime(feeding.end_time, include_seconds=True)}.\n"
            f"Duration: {duration:.0f} minutes.",
            reply_markup=reply_markup
        )
        return MAIN_MENU
    
    elif query.data == "back_to_menu":
        # Back to main menu
        reply_markup = InlineKeyboardMarkup(get_main_menu_keyboard())
        
        await query.edit_message_text(
            "What would you like to do?",
            reply_markup=reply_markup
        )
        return MAIN_MENU
    
    return FEEDING

async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """End current feeding session when /done command is used."""
    if "current_feeding_id" not in context.user_data and "feeding_id" not in context.user_data:
        await update.message.reply_text(
            "There is no active feeding session to end."
        )
        return await menu_command(update, context)
    
    db = get_db()
    feeding_id = context.user_data.get("current_feeding_id") or context.user_data.get("feeding_id")
    feeding = end_feeding(db, feeding_id)
    
    # Calculate duration
    duration = (feeding.end_time - feeding.start_time).total_seconds() / 60
    
    # Check if this is a bottle feeding without amount
    if feeding.type == FeedingType.BOTTLE and not feeding.amount:
        await update.message.reply_text(
            f"Bottle feeding ended at {format_datetime(feeding.end_time, include_seconds=True)}.\n"
            f"Duration: {duration:.0f} minutes.\n\n"
            f"Please enter the amount in ml or oz:"
        )
        return FEEDING_AMOUNT
    
    await update.message.reply_text(
        f"Feeding ended at {format_datetime(feeding.end_time, include_seconds=True)}.\n"
        f"Duration: {duration:.0f} minutes.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("↩️ Back to Menu", callback_data="back_to_menu")]
        ])
    )
    return MAIN_MENU

async def feeding_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle feeding amount input."""
    try:
        amount = float(update.message.text)
    except ValueError:
        await update.message.reply_text(
            "Please enter a valid number."
        )
        return FEEDING_AMOUNT
    
    db = get_db()
    feeding_id = context.user_data["feeding_id"]
    feeding = db.query(Feeding).filter(Feeding.id == feeding_id).first()
    
    if feeding:
        feeding.amount = amount
        db.commit()
    
    keyboard = [
        [InlineKeyboardButton("⏹️ End Feeding", callback_data="end_feeding")],
        [InlineKeyboardButton("↩️ Back to Menu", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"Amount recorded: {amount} ml/oz\n"
        "Press 'End Feeding' when done.",
        reply_markup=reply_markup
    )
    return FEEDING

async def change_baby_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle changing a baby's name."""
    new_name = update.message.text.strip()
    
    # Validate name
    if not new_name:
        await update.message.reply_text(
            "The name cannot be empty. Please enter a valid name."
        )
        return CHANGE_BABY_NAME
    
    # Update the baby's name in the database
    db = get_db()
    baby_id = context.user_data["baby_id"]
    
    # Import the update_baby_name function
    from database import update_baby_name
    
    baby = update_baby_name(db, baby_id, new_name)
    
    if baby:
        # Success message
        await update.message.reply_text(
            f"✅ Baby's name has been successfully changed to *{new_name}*.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("↩️ Back to Menu", callback_data="back_to_menu")]
            ])
        )
    else:
        # Error message
        await update.message.reply_text(
            "❌ Failed to update the baby's name. Please try again.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("↩️ Back to Settings", callback_data="back_to_settings")]
            ])
        )
    
    return MAIN_MENU

async def sleep_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle sleep actions."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "end_sleep":
        db = get_db()
        sleep_id = context.user_data["sleep_id"]
        sleep = end_sleep(db, sleep_id)
        
        # Calculate duration
        duration = (sleep.end_time - sleep.start_time).total_seconds() / 60
        
        keyboard = [
            [InlineKeyboardButton("↩️ Back to Menu", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"Sleep ended at {format_datetime(sleep.end_time, include_seconds=True)}.\n"
            f"Duration: {duration:.0f} minutes.",
            reply_markup=reply_markup
        )
        return MAIN_MENU
    
    elif query.data == "back_to_menu":
        # Back to main menu
        reply_markup = InlineKeyboardMarkup(get_main_menu_keyboard())
        
        await query.edit_message_text(
            "What would you like to do?",
            reply_markup=reply_markup
        )
        return MAIN_MENU
    
    return SLEEP

async def diaper_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle diaper type selection."""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("diaper_"):
        diaper_type = query.data.split("_")[1]
        
        if diaper_type == "wet":
            diaper_type_enum = DiaperType.WET
        elif diaper_type == "dirty":
            diaper_type_enum = DiaperType.DIRTY
        elif diaper_type == "both":
            diaper_type_enum = DiaperType.BOTH
        
        # Log diaper change
        db = get_db()
        baby_id = context.user_data["baby_id"]
        diaper = log_diaper_change(db, baby_id, diaper_type_enum)
        
        keyboard = [
            [InlineKeyboardButton("↩️ Back to Menu", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"{diaper_type.capitalize()} diaper change recorded at {format_datetime(diaper.time, include_seconds=True)}.",
            reply_markup=reply_markup
        )
        return MAIN_MENU
    
    elif query.data == "back_to_menu":
        # Back to main menu
        reply_markup = InlineKeyboardMarkup(get_main_menu_keyboard())
        
        await query.edit_message_text(
            "What would you like to do?",
            reply_markup=reply_markup
        )
        return MAIN_MENU
    
    return DIAPER_TYPE

async def crying_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle crying actions."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "end_crying":
        db = get_db()
        crying_id = context.user_data["crying_id"]
        crying = end_crying(db, crying_id)
        
        # Calculate duration
        duration = (crying.end_time - crying.start_time).total_seconds() / 60
        
        keyboard = [
            [InlineKeyboardButton("↩️ Back to Menu", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"Crying episode ended at {format_datetime(crying.end_time, include_seconds=True)}.\n"
            f"Duration: {duration:.0f} minutes.",
            reply_markup=reply_markup
        )
        return MAIN_MENU
    
    elif query.data.startswith("reason_"):
        reason = query.data.split("_")[1]
        
        if reason == "hungry":
            reason_enum = CryingReason.HUNGRY
            reason_text = "hungry"
        elif reason == "diaper":
            reason_enum = CryingReason.DIAPER
            reason_text = "needs a change of diapers"
        elif reason == "attention":
            reason_enum = CryingReason.ATTENTION
            reason_text = "just wants some attention"
        elif reason == "unknown":
            reason_enum = CryingReason.UNKNOWN
            reason_text = "has an unknown issue"
        
        # Update crying record with actual reason
        db = get_db()
        crying_id = context.user_data["crying_id"]
        crying = end_crying(db, crying_id, reason_enum)
        
        # Calculate duration
        duration = (crying.end_time - crying.start_time).total_seconds() / 60
        
        keyboard = [
            [InlineKeyboardButton("↩️ Back to Menu", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"Crying episode ended at {format_datetime(crying.end_time, include_seconds=True)}.\n"
            f"Duration: {duration:.0f} minutes.\n"
            f"Reason: Baby {reason_text}",
            reply_markup=reply_markup
        )
        return MAIN_MENU
    
    elif query.data == "back_to_menu":
        # Back to main menu
        reply_markup = InlineKeyboardMarkup(get_main_menu_keyboard())
        
        await query.edit_message_text(
            "What would you like to do?",
            reply_markup=reply_markup
        )
        return MAIN_MENU
    
    return CRYING

async def back_to_menu_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle back to menu action from various screens."""
    query = update.callback_query
    await query.answer()
    
    # Show main menu
    reply_markup = InlineKeyboardMarkup(get_main_menu_keyboard())
    
    await query.edit_message_text(
        "What would you like to do?",
        reply_markup=reply_markup
    )
    return MAIN_MENU

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors caused by updates."""
    logger.error("Exception while handling an update:", exc_info=context.error)

def main() -> None:
    """Start the bot."""
    # Get the token from environment variable
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("No TELEGRAM_BOT_TOKEN provided!")
        return
    
    # Create application
    application = Application.builder().token(token).build()
    
    # Create conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("menu", menu_command),
            CommandHandler("quick_bottle", quick_bottle_command),
            CommandHandler("done", done_command)
        ],
        states={
            SELECT_BABY: [
                CallbackQueryHandler(baby_selection)
            ],
            ADD_BABY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_baby_name)
            ],
            MAIN_MENU: [
                CallbackQueryHandler(main_menu)
            ],
            FEEDING_TYPE: [
                CallbackQueryHandler(feeding_type_selection)
            ],
            FEEDING: [
                CallbackQueryHandler(feeding_action),
                CommandHandler("done", done_command)
            ],
            FEEDING_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, feeding_amount)
            ],
            SLEEP: [
                CallbackQueryHandler(sleep_action)
            ],
            DIAPER_TYPE: [
                CallbackQueryHandler(diaper_type_selection)
            ],
            CRYING: [
                CallbackQueryHandler(crying_action)
            ],
            HISTORY: [
                CallbackQueryHandler(back_to_menu_action, pattern="back_to_menu")
            ],
            STATS: [
                CallbackQueryHandler(back_to_menu_action, pattern="back_to_menu")
            ],
            SETTINGS: [
                CallbackQueryHandler(main_menu)
            ],
            NATURAL_LANGUAGE_QUERY: [
                CallbackQueryHandler(back_to_menu_action, pattern="back_to_menu"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_natural_language_query)
            ],
            CHANGE_BABY_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, change_baby_name)
            ]
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("help", help_command),
            CommandHandler("menu", menu_command),
            CommandHandler("quick_bottle", quick_bottle_command),
            CommandHandler("done", done_command)
        ],
        allow_reentry=True
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("quick_bottle", quick_bottle_command))
    application.add_handler(CommandHandler("done", done_command))
    
    # Add natural language query handler outside the conversation
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_natural_language_query
    ))
    
    # Register error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main() 