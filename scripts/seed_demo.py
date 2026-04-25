#!/usr/bin/env python3
"""DEPRECATED: используется только для backward-compat с docker-compose.
Реальная логика в seed_demo_v2.py.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from seed_demo_v2 import main as v2_main

if __name__ == "__main__":
    print("⚠️  seed_demo.py is deprecated, delegating to seed_demo_v2.py")
    sys.exit(v2_main())
