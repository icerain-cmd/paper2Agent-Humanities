#!/usr/bin/env python3
from __future__ import annotations
import argparse, sys
from pathlib import Path
import uvicorn

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from paper2humanities.api import create_app

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--host",default="127.0.0.1")
    ap.add_argument("--port",type=int,default=8765)
    ap.add_argument("--model",default="gpt-6-sol")
    args=ap.parse_args()
    uvicorn.run(create_app(ROOT,args.model),host=args.host,port=args.port)

if __name__=="__main__":
    main()
