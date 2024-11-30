import os
import asyncio
import logging
import pandas as pd
import numpy as np
import pickle
import parselmouth
from joblib import load
from pyAudioAnalysis import ShortTermFeatures
from scipy.io import wavfile
from parselmouth.praat import call
from pydub import AudioSegment
from telegram.request import HTTPXRequest
from telegram import ForceReply, Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
from telegram.error import Forbidden

# Leer el token desde el archivo token.txt
with open('token_modelo.txt', 'r') as file:
    TOKEN = file.read().strip()

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Define conversation states
ASK_VOICE, ASK_CONFIRM = range(2)

# Audio instructions
audio_instructions = [
    "Graba el primer audio diciendo de manera sostenida la letra A, durante 3 segundos.",
    "Graba el segundo audio diciendo de manera sostenida la letra E, durante 3 segundos.",
    "Graba el tercer audio diciendo de manera sostenida la letra I, durante 3 segundos.",
    "Graba el cuarto audio diciendo de manera sostenida la letra O, durante 3 segundos.",
    "Graba el quinto audio diciendo de manera sostenida la letra U, durante 3 segundos.",
    "Graba el sexto audio contando de manera pausada los números del 0 al 9.",
]

# Carpeta donde se encuentran los modelos exportados
carpeta_modelos = 'modelos_exportados'

# Listas para cargar los modelos, escaladores y PCA
modelos_cargados = []
scalers_cargados = []
pca_cargados = []

# Leer los archivos de la carpeta
for i in range(6):  # Asumiendo que hay 6 modelos
    # Generar nombres de archivo
    nombre_modelo = f'modelo_{i + 1}.pkl'
    nombre_scaler = f'escalador_{i + 1}.pkl'
    nombre_pca = f'pca_{i + 1}.pkl'

    archivo_modelo = os.path.join(carpeta_modelos, nombre_modelo)
    archivo_scaler = os.path.join(carpeta_modelos, nombre_scaler)
    archivo_pca = os.path.join(carpeta_modelos, nombre_pca)

    # Cargar el modelo
    modelo = load(archivo_modelo)
    modelos_cargados.append(modelo)

    # Cargar el escalador
    scaler = load(archivo_scaler)
    scalers_cargados.append(scaler)

    # Cargar el PCA
    pca = load(archivo_pca)
    pca_cargados.append(pca)

def measure_feats(voiceID, f0min=75, f0max=500, unit="Hertz"):

    columns = [
            "F0_mean", "F0_std", "I_mean", "I_std", "hnr",
            "localJitter", "localabsoluteJitter", "rapJitter", "ppq5Jitter",
            "localShimmer", "localdbShimmer", "apq3Shimmer", "aqpq5Shimmer", "apq11Shimmer"
            ]

    try:
        sound = parselmouth.Sound(voiceID)

        pitch = call(sound, "To Pitch", 0.0, f0min, f0max)
        meanF0 = call(pitch, "Get mean", 0, 0, unit)
        stdevF0 = call(pitch, "Get standard deviation", 0 ,0, unit)

        intensity = call(sound, "To Intensity", 75, 0.0)
        meanI = call(intensity, "Get mean", 0, 0)
        stdevI = call(intensity, "Get standard deviation", 0 ,0)

        harmonicity = call(sound, "To Harmonicity (cc)", 0.01, 75, 0.1, 1.0)
        hnr = call(harmonicity, "Get mean", 0, 0)

        pointProcess = call(sound, "To PointProcess (periodic, cc)", f0min, f0max)
        localJitter = call(pointProcess, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3)
        localabsoluteJitter = call(pointProcess, "Get jitter (local, absolute)", 0, 0, 0.0001, 0.02, 1.3)
        rapJitter = call(pointProcess, "Get jitter (rap)", 0, 0, 0.0001, 0.02, 1.3)
        ppq5Jitter = call(pointProcess, "Get jitter (ppq5)", 0, 0, 0.0001, 0.02, 1.3)
        localShimmer =  call([sound, pointProcess], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
        localdbShimmer = call([sound, pointProcess], "Get shimmer (local_dB)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
        apq3Shimmer = call([sound, pointProcess], "Get shimmer (apq3)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
        aqpq5Shimmer = call([sound, pointProcess], "Get shimmer (apq5)", 0, 0, 0.0001, 0.02, 1.3, 1.6)
        apq11Shimmer =  call([sound, pointProcess], "Get shimmer (apq11)", 0, 0, 0.0001, 0.02, 1.3, 1.6)

        features = meanF0, stdevF0, meanI,stdevI, hnr, localJitter, localabsoluteJitter, rapJitter, ppq5Jitter, localShimmer, localdbShimmer, apq3Shimmer, aqpq5Shimmer, apq11Shimmer
        df = pd.DataFrame([features], columns=columns)

        return df
    except parselmouth.PraatError:
        
        print(voiceID)
        df = pd.DataFrame([0]*14, columns=columns)
        
        return df

def extract_estimators_from_audio(audio):
    Fs, x = wavfile.read(audio)
    if len(x.shape) > 1:
        x = np.mean(x, axis=1)
    F, f_names = ShortTermFeatures.feature_extraction(signal=x, sampling_rate=Fs, window=0.050*Fs, step=0.025*Fs, deltas=False)
    df = pd.DataFrame(F).T
    df.columns = f_names
    df_estimador = pd.DataFrame()
    for col in df.columns:

        df_estimador[f'{col}_mean'] = [df[col].mean()]
        df_estimador[f'{col}_std'] = [df[col].std()]

    return df_estimador

def extract_features_and_create_dataframe(audio):
    return pd.concat([extract_estimators_from_audio(audio), measure_feats(audio)], axis=1)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send a message when the command /start is issued."""
    logger.debug("Start command issued")
    await update.message.reply_html(rf"""¡Hola! Te doy la bienvenida. Este bot tiene cargado un modelo de Machine Learning entrenado para reconocer el sexo de una persona a partir de su voz.""")
    await asyncio.sleep(4)
    
    await update.message.reply_html(rf"""Te guiaré en la grabación y envío de tus audios, y luego trataré de adivinar cual es tu sexo.""")
    await asyncio.sleep(4)
    await update.message.reply_text("Empecemos.")
    
    context.user_data['audio_index'] = 0
    context.user_data['audio_files'] = []
    context.user_data['total_probability'] = 0
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
    audio_index = context.user_data['audio_index']
    
    # Define the folder based on the user's data
    folder = 'audios'        
    subfolder = f'audio_{audio_index + 1}'
    
    full_folder_path = os.path.join(folder, subfolder)
    if not os.path.exists(full_folder_path):
        os.makedirs(full_folder_path)

    # Save the file in the correct folder
    file_id = context.user_data['file_id']
    new_file = await context.bot.get_file(file_id)
    ogg_path = os.path.join(full_folder_path, f"audio_{audio_index + 1}.ogg")
    wav_path = os.path.join(full_folder_path, f"audio_{audio_index + 1}.wav")

    await new_file.download_to_drive(ogg_path)

    # Convert the file to WAV format and save it in the same folder
    audio = AudioSegment.from_ogg(ogg_path)
    audio.export(wav_path, format="wav")
    os.remove(ogg_path)
    
    # Extract features
    data = extract_features_and_create_dataframe(wav_path)
    #data = data.drop(columns=['category'])
    
    # Apply scaler, PCA and model for the current audio
    scaled_data = scalers_cargados[audio_index].transform(data)
    pca_data = pca_cargados[audio_index].transform(scaled_data)
    probability = modelos_cargados[audio_index].predict_proba(pca_data)[:, 1]  # Probability of being 'Hombre'
    
    # Accumulate probabilities
    context.user_data['total_probability'] += probability[0]

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
            await query.message.reply_text(f"Audio cargado con éxito.")
            await asyncio.sleep(1)
            
            await query.message.reply_text(f"{audio_instructions[audio_index]}")
            return ASK_VOICE
        else:
            total_probability = context.user_data['total_probability']
            average_probability = total_probability / len(audio_instructions)
            
            await query.message.reply_text(f"Audio cargado con éxito.")
            await asyncio.sleep(1)

            await query.message.reply_text("¡Has completado todas las grabaciones!")
            await asyncio.sleep(2)
            
            await query.message.reply_text("Procesando...")
            await asyncio.sleep(4)
            
            # Condiciones para imprimir el mensaje adecuado
            if average_probability > 0.5:
                await query.message.reply_text(f"Hay un {average_probability:.0%} de probabilidad que seas Hombre.")
                await asyncio.sleep(3)
                await query.message.reply_text(f"Si deseas probar de nuevo, haz click /aqui.")
            
            elif average_probability < 0.5:
                await query.message.reply_text(f"Hay un {(1 - average_probability):.0%} de probabilidad que seas Mujer.")
                await asyncio.sleep(3)
                await query.message.reply_text(f"Si deseas probar de nuevo, haz click /aqui.")
            
            else:
                await query.message.reply_text("No pude decidirme. Por favor, prueba nuevamente haciendo click /aqui")
                await asyncio.sleep(2)
            
            return ConversationHandler.END
    else:
        os.remove(context.user_data['audio_files'].pop())
        await query.message.reply_text("Audio desechado. Por favor, graba nuevamente:")
        return ASK_VOICE

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    logger.debug("Conversation canceled by user")
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
            ASK_VOICE: [MessageHandler(filters.VOICE & ~filters.COMMAND, ask_voice)],
            ASK_CONFIRM: [CallbackQueryHandler(confirm_audio)],
            },
        fallbacks=[CommandHandler("cancelar", cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(timeout = 20)

if __name__ == "__main__":
    main()

