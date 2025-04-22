#!/bin/env bash
# requires see's if the utility is installed
requires() {
  if ! [ -x "$(command -v $1)" ]; then
    echo Error: "$1" is not installed. >&2
    if [ -n "$2" ]; then
      echo "Install with $2" >&2
      fi
    exit 1
  fi
}