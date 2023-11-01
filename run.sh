#!/usr/bin/env bash

export $(grep -v '^#' .env | xargs)

uvicorn smp_submitter:app --reload
