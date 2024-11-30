import os
import pickle
import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
from sklearn.model_selection import StratifiedKFold
from sklearn.linear_model import LogisticRegression

# Ruta de la carpeta que contiene los archivos CSV
input_dir = './csv'

# Diccionario para almacenar los dataframes
dataframes = {}

# Leer cada archivo CSV de la carpeta y convertirlo a un dataframe
print(f'Leyendo archivos CSV desde la carpeta {input_dir}...')
for file_name in os.listdir(input_dir):
    if file_name.endswith('.csv'):
        file_path = os.path.join(input_dir, file_name)
        print(f'Leyendo {file_name}...')
        df = pd.read_csv(file_path)
        # Guardar el dataframe en el diccionario con el nombre del archivo sin extensión como clave
        dataframes[file_name.replace('.csv', '')] = df
        print(f'{file_name} leído y convertido a dataframe.')

print('Lectura de archivos completada.')

# Función para elegir el número óptimo de componentes
def elegir_componentes(varianza_acumulada, varianza_diferencia, umbral_varianza=0.7, umbral_incremento=0.05):
    for i in range(len(varianza_acumulada)):
        if varianza_acumulada[i] >= umbral_varianza:
            if i + 1 < len(varianza_diferencia) and varianza_diferencia[i + 1] < umbral_incremento:
                return i + 1
    return len(varianza_acumulada)

# Listas para guardar modelos, escaladores y PCA entrenados
modelos_entrenados = []
scalers_entrenados = []
pca_entrenados = []
resultados = []

# Procesamiento de cada dataframe
for name, df in dataframes.items():
    print(f'\nProcesando el dataset: {name}')

    # Separar características y etiquetas
    X = df.drop(columns=['category'])
    y = df['category'].replace({'Hombre': 1, 'Mujer': 0})

    # Estandarización en todo el conjunto de datos
    print(' - Estandarizando las características...')
    scaler = StandardScaler().fit(X)
    X_standar = scaler.transform(X)
    #X_standar = pd.DataFrame(X_standar, columns=X.columns)

    # Aplicación de PCA en todo el conjunto de datos
    print(' - Aplicando PCA y seleccionando número óptimo de componentes...')
    pca = PCA()
    pca.fit(X_standar)
    varianza_explicada = pca.explained_variance_ratio_
    varianza_acumulada = varianza_explicada.cumsum()
    varianza_diferencia = np.diff(varianza_acumulada, prepend=0)

    n_componentes_optimo = elegir_componentes(varianza_acumulada, varianza_diferencia)
    print(f' - Número óptimo de componentes seleccionados: {n_componentes_optimo}')

    # Reducir el conjunto de datos usando el número de componentes seleccionados
    pca = PCA(n_components=n_componentes_optimo).fit(X_standar)
    X_pca = pca.transform(X_standar)

    # Validación cruzada con 5 pliegues
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    accuracy_promedio = 0

    for fold, (train_index, test_index) in enumerate(cv.split(X_pca, y)):
        print(f'   - Fold {fold + 1}: Entrenando modelo...')
        X_train, X_test = X_pca[train_index], X_pca[test_index]
        y_train, y_test = y.values[train_index], y.values[test_index]

        # Entrenamiento temporal en cada pliegue
        model = LogisticRegression()
        model.fit(X_train, y_train)

        # Evaluación del modelo en este pliegue
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        accuracy_promedio += accuracy
        print(f'   - Fold {fold + 1}: Accuracy = {accuracy * 100.0:.2f}%')

    accuracy_promedio /= 5
    print(f' - Accuracy promedio para el Audio_{name}: {accuracy_promedio * 100.0:.2f}%')

    # Entrenar el modelo, escalador y PCA final en todo el conjunto de datos
    print(' - Entrenando modelo final en todo el conjunto de datos...')
    model_final = LogisticRegression()
    model_final.fit(X_pca, y)

    # Guardar el modelo, escalador y PCA entrenados
    modelos_entrenados.append(model_final)
    scalers_entrenados.append(scaler)
    pca_entrenados.append(pca)

print('\nProceso completado para todos los datasets.')

# Crear la carpeta de destino si no existe
carpeta_destino = 'modelos_exportados'
if not os.path.exists(carpeta_destino):
    os.makedirs(carpeta_destino)

# Exportar modelos, escaladores y PCA
for i, (modelo, escalador, pca) in enumerate(zip(modelos_entrenados, scalers_entrenados, pca_entrenados)):
    # Crear nombres de archivo únicos
    archivo_modelo = os.path.join(carpeta_destino, f'modelo_{i+1}.pkl')
    archivo_scaler = os.path.join(carpeta_destino, f'escalador_{i+1}.pkl')
    archivo_pca = os.path.join(carpeta_destino, f'pca_{i+1}.pkl')

    # Guardar el modelo
    with open(archivo_modelo, 'wb') as file:
        pickle.dump(modelo, file)
    print(f'Modelo {i+1} exportado como {archivo_modelo}')

    # Guardar el escalador
    with open(archivo_scaler, 'wb') as file:
        pickle.dump(escalador, file)
    print(f'Scaler {i+1} exportado como {archivo_scaler}')

    # Guardar el PCA
    with open(archivo_pca, 'wb') as file:
        pickle.dump(pca, file)
    print(f'PCA {i+1} exportado como {archivo_pca}')


