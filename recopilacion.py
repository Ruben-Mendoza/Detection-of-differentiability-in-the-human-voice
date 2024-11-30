import os
import asyncio
import logging
from pydub import AudioSegment
from telegram.request import HTTPXRequest
from telegram import ForceReply, Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler, CallbackQueryHandler

# Leer el token desde el archivo token.txt
with open('token_recoppilacion.txt', 'r') as file:
    TOKEN = file.read().strip()

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Define conversation states
ASK_USERNAME, ASK_SEX, ASK_AGE, ASK_SMOKER, ASK_CIGARETTES_PER_DAY, ASK_YEARS_SMOKING, ASK_VOICE, ASK_CONFIRM, ASK_RATING, ASK_FEEDBACK, ASK_FEEDBACK_MESSAGE = range(11)

# File to store user names
USER_FILE = "nombres.txt"

# Verificar y crear "nombres.txt" si no existe
if not os.path.exists(USER_FILE):
    with open(USER_FILE, 'w') as file:
        file.write("")

# Audio instructions
audio_instructions = [
    "Por favor, graba el primer audio diciendo de manera sostenida la letra A, durante 5 segundos.",
    "Por favor, graba el segundo audio diciendo de manera sostenida la letra E, durante 5 segundos.",
    "Por favor, graba el tercer audio diciendo de manera sostenida la letra I, durante 5 segundos.",
    "Por favor, graba el cuarto audio diciendo de manera sostenida la letra O, durante 5 segundos.",
    "Por favor, graba el quinto audio diciendo de manera sostenida la letra U, durante 5 segundos.",
    "Por favor, graba el sexto audio contando de manera pausada los números del 0 al 9.",
]

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send a message when the command /start is issued."""
    logger.debug("Start command issued")
    await update.message.reply_html(rf"""¡Hola! Te doy la bienvenida a este bot de recopilación de audios para un proyecto sobre el efecto del cigarrillo en la voz.""")
    await asyncio.sleep(4)
    
    await update.message.reply_html(rf"""Te haremos algunas preguntas para entender el contexto de los audios. No te preocupes, no pediremos datos sensibles.""")
    await asyncio.sleep(4)
    
    await update.message.reply_html(rf"""Luego, deberás grabar 6 audios siguiendo instrucciones simples. Te pedimos que sigas estas instrucciones con cuidado para que los datos sean lo más precisos posible.""")
    await asyncio.sleep(5)
    
    await update.message.reply_html(rf"""Podrás reiniciar la encuesta en cualquier momento escribiendo el comando "/cancelar" en la celda de mensaje y enviándolo.""")
    await asyncio.sleep(5)
    
    await update.message.reply_html(rf"""Esto borrará todas las respuestas ingresadas hasta el momento. Luego podrás volver a empezar si lo deseas.""")
    await asyncio.sleep(4)
    
    await update.message.reply_html(rf"""Esta encuesta es personal, solo tenes que responderla una única vez. Por favor, no la dejes incompleta.""")       
    await asyncio.sleep(4)
    
    await update.message.reply_html(rf"""Te recomendamos tener buena conexión a internet, preferentemente Wifi, ya que usar datos móviles podría causar retrasos o interrupciones en el bot.""")
    await asyncio.sleep(5)
    
    await update.message.reply_html(rf"""Para identificar tus audios y no confundirlos con los de otros encuestados, deberás ingresar un nombre de usuario.""")
    await asyncio.sleep(4)
    
    await update.message.reply_html(rf"""Si ya está en uso, deberás elegir uno nuevo. Este puede ser ficticio, un código númerico o una combinacíon de letras y números.""")
    await asyncio.sleep(5)
    
    await update.message.reply_html(rf"""Si luego de ingresarlo no obtienes respuestas del bot, haz click "/aqui".""")
    await asyncio.sleep(3)
    
    await update.message.reply_text("Empecemos. Ingresa el nombre de usuario: ")
    return ASK_USERNAME

async def ask_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle user name input and check for uniqueness."""
    logger.debug("ask_username called")
    user_name = update.message.text.strip()
    if not user_name:
        await update.message.reply_text("El nombre de usuario no puede estar vacío. Por favor, ingresa un nombre de usuario:")
        return ASK_USERNAME

    if is_username_taken(user_name):
        await update.message.reply_text("Este nombre ya fue utilizado. Por favor, ingresa uno nuevo:")
        return ASK_USERNAME

    context.user_data['user_name'] = user_name
    await update.message.reply_text(f"Excelente {user_name}, hemos registrado tu nombre. Continuemos.")

    keyboard = [
        [
            InlineKeyboardButton("Hombre", callback_data='hombre'),
            InlineKeyboardButton("Mujer", callback_data='mujer'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Elige una opción:", reply_markup=reply_markup)
    return ASK_SEX

def is_username_taken(user_name: str) -> bool:
    """Check if the user name is already taken."""
    logger.debug(f"Checking if username '{user_name}' is taken")
    if os.path.exists(USER_FILE):
        with open(USER_FILE, 'r') as file:
            return any(line.split()[0] == user_name for line in file if line.split())
    return False

def save_user_data(user_data: dict) -> None:
    """Save the user data to the file."""
    logger.debug(f"Saving user data: {user_data}")
    with open(USER_FILE, 'a') as file:
        file.write(f"{user_data['user_name']}    {user_data['sex']}    {user_data['age']}    {user_data['smoker']}    {user_data['cigarettes_per_day']}    {user_data['years_smoking']}\n")

async def ask_sex(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask for the user's sex."""
    logger.debug("ask_sex called")
    query = update.callback_query
    await query.answer()
    sex = query.data
    context.user_data['sex'] = sex
    await query.edit_message_text(text=f"Perfecto, has elegido: {sex.capitalize()}.")
    await query.message.reply_text("Ahora, por favor ingresa tu edad (Solo el número).")
    return ASK_AGE

async def ask_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask for the user's age."""
    logger.debug("ask_age called")
    try:
        age = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Por favor, ingresa un número válido para tu edad:")
        return ASK_AGE
        
    context.user_data['age'] = age
    await update.message.reply_text(f"Hemos registrado tu edad como {age}.")
    await asyncio.sleep(1)
    await update.message.reply_text(f"Sigamos.")

    keyboard = [
        [
            InlineKeyboardButton("Sí", callback_data='si'),
            InlineKeyboardButton("No", callback_data='no'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("¿Eres fumador/a?. Elige una opción:", reply_markup=reply_markup)
    return ASK_SMOKER

async def ask_smoker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
	"""Ask if the user smokes."""
	logger.debug("ask_smoker called")
	query = update.callback_query
	await query.answer()
	smoker = query.data
	context.user_data['smoker'] = smoker
	
	await query.edit_message_text(text=f"Has indicado que {smoker.capitalize()} eres fumador/a.")
	await asyncio.sleep(1)
    
	if smoker == "si":
		await query.message.reply_text("¿Cuántos cigarrillos fumas aproximadamente al día? Por favor, ingresa un número.")
		return ASK_CIGARETTES_PER_DAY
    	
	else:
		await query.message.reply_text("""Ahora te guiaremos en la grabación y envío de los audios.""")
		await asyncio.sleep(4)
    
		await query.message.reply_text("""Ten en cuenta estas recomendaciones:""")
		await asyncio.sleep(3)
    
		await query.message.reply_text("""1) Evita grabar en lugares con mucho eco, como baños o espacios pequeños.""")
		await asyncio.sleep(3)
    
		await query.message.reply_text("""2) Trata de evitar ruido externo, como ruidos de tránsito, música, televisión, etc. Lo importante es captar tu voz lo más clara posible.""")
		await asyncio.sleep(5)
		
		await query.message.reply_text("""3) Mantén una postura cómoda. Hazlo sentado o parado.""")
		await asyncio.sleep(4)
    
		await query.message.reply_text("""4) Si la grabación no sale bien, podrás desechar el audio y grabarlo otra vez, todas las veces que necesites.""")
		await asyncio.sleep(5)
		
		await query.message.reply_text("""5) En caso de enviar un audio y no obtener respuesta luego de unos segundos, vuelve a grabar y enviar el audio siguiendo las mismas instrucciones.""")
		await asyncio.sleep(5)
		
		await query.message.reply_text("""6) Si deseas reiniciar la encuesta, presiona el siguiente comando: /cancelar. Tambien puedes escribirlo y enviarlo en cualquier momento.""")
		await asyncio.sleep(5)
		
		await query.message.reply_text("Ahora sí, empecemos.")
		await asyncio.sleep(2)
        
		context.user_data['cigarettes_per_day'] = 0
		context.user_data['years_smoking'] = 0
        
		save_user_data(context.user_data)
		context.user_data['audio_index'] = 0
		context.user_data['audio_files'] = []
		await query.message.reply_text(audio_instructions[context.user_data['audio_index']])

		return ASK_VOICE

async def ask_cigarettes_per_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask for the number of cigarettes smoked per day."""
    logger.debug("ask_cigarettes_per_day called")
    try:
        cigarettes_per_day = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Por favor, ingresa un número válido para la cantidad de cigarrillos por día:")
        return ASK_CIGARETTES_PER_DAY
    context.user_data['cigarettes_per_day'] = cigarettes_per_day
    await update.message.reply_text(f"Entendido, aproximadamente {cigarettes_per_day} cigarrillos por día.")
    await asyncio.sleep(1)
    await update.message.reply_text(f"Ahora, dinos cuántos años llevas fumando. Si llevas menos de un año, ingresa solo 1.")
    return ASK_YEARS_SMOKING

async def ask_years_smoking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask for the number of years the user has been smoking."""
    logger.debug("ask_years_smoking called")
    try:
        years_smoking = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Por favor, ingresa un número válido para los años que llevas fumando:")
        return ASK_YEARS_SMOKING
        
    context.user_data['years_smoking'] = years_smoking
    save_user_data(context.user_data)
    
    # Instrucciones generales antes de grabar audios
    await update.message.reply_text("""Ahora te guiaremos en la grabación y envío de los audios.""")
    await asyncio.sleep(4)
    
    await update.message.reply_text("""Ten en cuenta estas recomendaciones:""")
    await asyncio.sleep(3)
    
    await update.message.reply_text("""1) Evita grabar en lugares con mucho eco, como baños o espacios pequeños.""")
    await asyncio.sleep(4)
    
    await update.message.reply_text("""2) Trata de evitar ruido externo, como ruidos de tránsito, música, televisión, etc. Lo importante es captar tu voz lo más clara posible.""")
    await asyncio.sleep(5)
    
    await update.message.reply_text("""3) Mantén una postura cómoda. Hazlo sentado o parado.""")
    await asyncio.sleep(4)
    
    await update.message.reply_text("""4) Si la grabación no sale bien, podrás desechar el audio y grabarlo otra vez, todas las veces que necesites.""")
    await asyncio.sleep(5)
    
    await update.message.reply_text("""5) En caso de enviar un audio y no obtener respuesta luego de unos segundos, vuelve a grabar y enviar el audio siguiendo las mismas instrucciones.""")
    await asyncio.sleep(5)
    
    await update.message.reply_text("""6) Si deseas reiniciar la encuesta, presiona el siguiente comando: /cancelar. Tambien puedes escribirlo y enviarlo en cualquier momento.""")
    await asyncio.sleep(5)
    
    await update.message.reply_text("Ahora sí, empecemos.")
    await asyncio.sleep(2)
    
    context.user_data['audio_index'] = 0
    context.user_data['audio_files'] = []
    await update.message.reply_text(audio_instructions[context.user_data['audio_index']])
    return ASK_VOICE

async def ask_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask for confirmation of the audio."""
    logger.debug("ask_confirm called")
    keyboard = [
        [
            InlineKeyboardButton("Confirmar", callback_data='confirmar'),
            InlineKeyboardButton("Repetir", callback_data='repetir'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Por favor, confirma si el audio es correcto o si quieres repetir la grabación:", reply_markup=reply_markup)
    return ASK_CONFIRM

async def download_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Download the voice message."""
    logger.debug("download_voice called")
    user_name = context.user_data['user_name']
    audio_index = context.user_data['audio_index']
    sex = context.user_data['sex']
    smoker = context.user_data['smoker']

    # Define the folder based on the user's data
    folder = ''
    if sex == 'hombre' and smoker == 'si':
        folder = 'Hombre_Fuma'
    elif sex == 'hombre' and smoker == 'no':
        folder = 'Hombre_No_Fuma'
    elif sex == 'mujer' and smoker == 'si':
        folder = 'Mujer_Fuma'
    elif sex == 'mujer' and smoker == 'no':
        folder = 'Mujer_No_Fuma'
        
    subfolder = f'audio_{audio_index + 1}'
    
    full_folder_path = os.path.join(folder, subfolder)
    if not os.path.exists(full_folder_path):
        os.makedirs(full_folder_path)

    # Save the file in the correct folder
    file_id = context.user_data['file_id']
    new_file = await context.bot.get_file(file_id)
    ogg_path = os.path.join(full_folder_path, f"{user_name}.ogg")
    wav_path = os.path.join(full_folder_path, f"{user_name}.wav")

    await new_file.download_to_drive(ogg_path)

    # Convert the file to WAV format and save it in the same folder
    audio = AudioSegment.from_ogg(ogg_path)
    audio.export(wav_path, format="wav")
    os.remove(ogg_path)

    context.user_data['audio_files'].append(wav_path)
    logger.debug(f"Downloaded and converted {ogg_path} to {wav_path}")

async def ask_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the voice message and ask for confirmation."""
    logger.debug("ask_voice called")
    if not update.message.voice:
        await update.message.reply_text("No se detectó ningún mensaje de voz. Por favor, intenta de nuevo.")
        return ASK_VOICE

    # Guardar el file_id del mensaje de voz en context.user_data
    context.user_data['file_id'] = update.message.voice.file_id
    
    await update.message.reply_text("""Cargando...""")
    
    try:
        await download_voice(update, context)
        await asyncio.sleep(2)
        
        return await ask_confirm(update, context)
        
    except Exception as e:
        logger.error(f"Error downloading or converting audio: {e}")
        await update.message.reply_text("Ha ocurrido un error, vuelve a grabar y enviar el audio.")
        return ASK_VOICE

async def confirm_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirm the audio and proceed to the next one."""
    logger.debug("confirm_audio called")
    query = update.callback_query
    await query.answer()
    if query.data == 'confirmar':
        audio_index = context.user_data['audio_index'] + 1
        context.user_data['audio_index'] = audio_index
        
        if audio_index < len(audio_instructions):
            await query.message.reply_text(f"Audio guardado con éxito.")
            await asyncio.sleep(1)
            
            await query.message.reply_text(f"{audio_instructions[audio_index]}")
            return ASK_VOICE
        else:
            await query.message.reply_text(f"Audio guardado con éxito.")
            await asyncio.sleep(1)

            await query.message.reply_text("¡Has completado todas las grabaciones!")
            await asyncio.sleep(2)

            await query.message.reply_text("Todos los audios han sido guardados correctamente.")
            await asyncio.sleep(2)

            # Preguntar sobre la experiencia de uso
            keyboard = [
                [
                    InlineKeyboardButton("Sí", callback_data='rating_yes'),
                    InlineKeyboardButton("No", callback_data='rating_no'),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text("¿Deseas calificar tu experiencia de uso de este bot?", reply_markup=reply_markup)
            return ASK_RATING
    else:
        os.remove(context.user_data['audio_files'].pop())
        await query.message.reply_text("Audio desechado. Por favor, graba nuevamente:")
        return ASK_VOICE

async def ask_rating(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask for user rating on a scale of 1 to 5."""
    logger.debug("ask_rating called")
    query = update.callback_query
    await query.answer()
    if query.data == 'rating_yes':
    
        keyboard = [
            [InlineKeyboardButton(str(i), callback_data=f'rating_{i}') for i in range(1, 6)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Por favor, califica tu experiencia del 1 al 5, donde 1 es muy mala y 5 es excelente.", reply_markup = reply_markup)
        return ASK_FEEDBACK
    
    else:
        await query.message.reply_text("Muchas gracias por tu participación. ¡Nos vemos!")
        await asyncio.sleep(2)
        await query.message.reply_text("(Si deseas reiniciar la encuesta para que otra persona la llene, haz click /aqui.)")
        return ConversationHandler.END

async def ask_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's rating and ask for feedback message."""
    logger.debug("ask_feedback_message called")
    query = update.callback_query
    await query.answer()
    
    rating = int(query.data.split('_')[1])
    context.user_data['rating'] = rating
    
    await query.message.reply_text(f"Has calificado tu experiencia con un {rating}/5.")
    
    keyboard = [
        [
            InlineKeyboardButton("Sí", callback_data='si'),
            InlineKeyboardButton("No", callback_data='no'),
        ]
    ]
	
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("¿Deseas dejar un mensaje con sugerencias o aclaraciones?", reply_markup=reply_markup)

    return ASK_FEEDBACK_MESSAGE

async def ask_feedback_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle feedback message input."""
    logger.debug("ask_feedback_message called")
    query = update.callback_query
    await query.answer()
    
    choice = query.data
    if choice == "si":
        await query.edit_message_text("A continuación escribe y envía tu mensaje. Siéntete libre de escribir lo que quieras, lo leeremos atentamente.")
        return ASK_FEEDBACK_MESSAGE
    else:
        # Guardar una cadena vacía como comentario si el usuario elige no dejar feedback
        context.user_data['feedback_message'] = " "
        return await save_feedback_message(update, context)

feedback_file = "calificaciones.txt"

# Verificar y crear "calificaciones.txt" si no existe
if not os.path.exists(feedback_file):
    with open(feedback_file, 'w') as file:
        file.write("")

async def save_feedback_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Save feedback message and end the conversation."""
    logger.debug("save_feedback_message called")
    feedback_message = context.user_data.get('feedback_message', 
                                         update.message.text.strip() if update.message and update.message.text else " ")

    user_data = context.user_data
    user_name = user_data.get('user_name', 'Unknown')  # Suponiendo que tienes el ID o nombre del usuario
    rating = user_data.get('rating', 'N/A')

    # Actualizar o agregar la línea correspondiente en el archivo nombres.txt
    feedback_lines = []
    user_found = False

    # Leer el archivo y actualizar la línea correspondiente al usuario
    if os.path.exists(feedback_file):
        with open(feedback_file, "r") as file:
            feedback_lines = file.readlines()

        for i, line in enumerate(feedback_lines):
            if line.startswith(f"Usuario: {user_name},"):
                feedback_lines[i] = f"{user_name}    {rating}    {feedback_message}\n"
                user_found = True
                break

    # Si el usuario no se encontró, agregar una nueva línea
    if not user_found:
        feedback_lines.append(f"{user_name}    {rating}    {feedback_message}\n")

    # Guardar el archivo actualizado
    with open(feedback_file, "w") as file:
        file.writelines(feedback_lines)

    # Determinar el tipo de actualización y responder adecuadamente
    if update.message:
        await update.message.reply_text("Muchas gracias por tu participación. ¡Nos vemos!", reply_markup=ReplyKeyboardRemove())
        await asyncio.sleep(2)
        await update.message.reply_text("(Si deseas reiniciar la encuesta para que otra persona la llene, haz click /aqui.)")
    
    elif update.callback_query:
        await update.callback_query.message.reply_text("Muchas gracias por tu participación. ¡Nos vemos!", reply_markup=ReplyKeyboardRemove())
        await asyncio.sleep(2)
        await update.callback_query.message.reply_text("(Si deseas reiniciar la encuesta para que otra persona la llene, haz click /aqui.)")
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    logger.debug("Conversation canceled by user")
    user_data = context.user_data
    user_name = user_data.get('user_name', 'NoName')
    
    lines_to_keep = []
    
    if os.path.exists(USER_FILE):
        with open(USER_FILE, 'r') as file:
            lines = file.readlines()
            
        lines_to_keep = [line for line in lines if not line.startswith(user_name)]
        
        with open(USER_FILE, 'w') as file:
            file.writelines(lines_to_keep)
            
    await update.message.reply_text("Encuesta cancelada.")
    await asyncio.sleep(1)
    await update.message.reply_text("Si deseas comenzar de nuevo, haz click /aqui.")
    return ConversationHandler.END

def main() -> None:
    
    application = Application.builder().token(TOKEN).build()

    # Add conversation handler with the states ASK_USERNAME, ASK_SEX, ASK_AGE, ASK_SMOKER, ASK_CIGARETTES_PER_WEEK, ASK_YEARS_SMOKING, ASK_VOICE, ASK_CONFIRM
    conv_handler = ConversationHandler(
        entry_points=[
            
            CommandHandler("start", start),
            CommandHandler("aqui", start)
        
        ],
        states={
            ASK_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_username)],
            ASK_SEX: [CallbackQueryHandler(ask_sex)],
            ASK_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_age)],
            ASK_SMOKER: [CallbackQueryHandler(ask_smoker)],
            ASK_CIGARETTES_PER_DAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_cigarettes_per_day)],
            ASK_YEARS_SMOKING: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_years_smoking)],
            ASK_VOICE: [MessageHandler(filters.VOICE & ~filters.COMMAND, ask_voice)],
            ASK_CONFIRM: [CallbackQueryHandler(confirm_audio)],
            ASK_RATING: [CallbackQueryHandler(ask_rating)],
            ASK_FEEDBACK: [CallbackQueryHandler(ask_feedback), MessageHandler(filters.TEXT, ask_feedback)],
            ASK_FEEDBACK_MESSAGE: [CallbackQueryHandler(ask_feedback_message),
            MessageHandler(filters.TEXT & ~filters.COMMAND, save_feedback_message)],
        },
        fallbacks=[CommandHandler("cancelar", cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(timeout = 20)

if __name__ == "__main__":
    main()

