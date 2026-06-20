@echo off
title Flowise - ContactCenterCustomerService (port 3002)
if not exist flowise-data mkdir flowise-data
if not exist flowise-data\logs mkdir flowise-data\logs
if not exist flowise-data\storage mkdir flowise-data\storage
set PORT=3002
set DATABASE_PATH=%~dp0flowise-data\database.sqlite
set APIKEY_PATH=%~dp0flowise-data
set SECRETKEY_PATH=%~dp0flowise-data
set LOG_PATH=%~dp0flowise-data\logs
set BLOB_STORAGE_PATH=%~dp0flowise-data\storage
flowise start
