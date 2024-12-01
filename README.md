# Voice Gender Classification with Telegram Bot

This repository contains four main files, each serving a specific function in the voice gender classification project using a Telegram bot.

### Files Overview

1. "**recopilacion.py**"  
   This script contains the Telegram bot that allows anyone to interact with the bot by answering a few questions and sending their audio recordings. It collects the data that will be used for analysis.

2. "**extraccion.py**"  
   This script extracts the relevant acoustic features from each audio recording and stores them in a CSV file for further analysis.

3. "**entrenamiento.py**"  
   This script takes the extracted CSV files, processes the data, and trains Logistic Regression models for the classification task.

4. **bot_modelos.py**  
   This is the Telegram bot responsible for classifying incoming audio recordings. It uses the pre-trained models to estimate the probability that the speaker is either male or female.

### Setup Instructions

**Create Telegram Bots and Tokens**  
   To use the Telegram bots, you must first create them using the [Telegram Bot API](https://core.telegram.org/bots#botfather). After creating each bot, you will receive a unique API token. Save these tokens in two text files:
   - `token_recopilacion.txt` for the data collection bot.
   - `token_modelos.txt` for the classification bot.
