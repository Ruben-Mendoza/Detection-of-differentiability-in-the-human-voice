import os
import random
import pandas as pd
import numpy as np
import inspect
import librosa
import math
import parselmouth
import joblib
from parselmouth.praat import call
from pyAudioAnalysis import audioBasicIO, ShortTermFeatures

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
    
def extract_estimators_from_audio(audio_file_path):

        Fs, x = audioBasicIO.read_audio_file(audio_file_path)
        F, f_names = ShortTermFeatures.feature_extraction(signal = x,
                                                          sampling_rate = Fs,
                                                          window = 0.050*Fs,
                                                          step = 0.025*Fs,
                                                          deltas=False)

        df = pd.DataFrame(F).T
        df.columns = f_names

        df_estimador = pd.DataFrame()

        for col in df.columns:
            df_estimador[f'{col}_mean'] = [df[col].mean()]
            df_estimador[f'{col}_std'] = [df[col].std()]

        return df_estimador
        
def extract_features_and_create_dataframe(folder_path, category_1):
    print(f'Extrayendo características de la carpeta: {folder_path}\n')
    final_df = pd.DataFrame()

    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)
        if os.path.isfile(file_path):
            print(f'Procesando archivo: {file_name}')
            df_fila = pd.concat([extract_estimators_from_audio(file_path),
                                measure_feats(file_path, f0min=75, f0max=500, unit="Hertz")],
                                axis=1)
            final_df = pd.concat([final_df, df_fila], ignore_index=True)

    final_df['category'] = category_1

    print(f'\nCaracterísticas extraídas para {folder_path}.')
    return final_df

# Diccionario para almacenar los dataframes de cada conjunto de audios
dataframes = {}

# Directorio base donde se encuentran las carpetas de los audios
base_dir = './'

# Iterar sobre las 6 carpetas de audios
for i in range(1, 7):
    print(f'Procesando audios en la carpeta {i}...')

    men_1_folder_path = os.path.join(base_dir, f'Hombre_Fuma/audio_{i}')
    men_2_folder_path = os.path.join(base_dir, f'Hombre_No_Fuma/audio_{i}')
    women_1_folder_path = os.path.join(base_dir, f'Mujer_Fuma/audio_{i}')
    women_2_folder_path = os.path.join(base_dir, f'Mujer_No_Fuma/audio_{i}')

    men_1_df = extract_features_and_create_dataframe(men_1_folder_path, category_1=1)
    men_2_df = extract_features_and_create_dataframe(men_2_folder_path, category_1=1)
    women_1_df = extract_features_and_create_dataframe(women_1_folder_path, category_1=0)
    women_2_df = extract_features_and_create_dataframe(women_2_folder_path, category_1=0)

    print(f'Concatenando dataframes para la iteración {i}...')
    df = pd.concat([men_1_df, women_1_df, men_2_df, women_2_df], ignore_index=True)
    df = df.sample(frac=1).reset_index(drop=True)
    dataframes[f'audio_{i}'] = df
    print(f'Dataframe para audio_{i} creado y almacenado.\n')

# Exportar cada dataframe a un archivo CSV
output_dir = './csv'
os.makedirs(output_dir, exist_ok=True)

print(f'Exportando dataframes a la carpeta {output_dir}...\n')
for key, df in dataframes.items():
    csv_path = os.path.join(output_dir, f'{key}.csv')
    df.to_csv(csv_path, index=False)
    print(f'Dataframe {key} exportado a {csv_path}')
    
print('\nExportación completada.')

