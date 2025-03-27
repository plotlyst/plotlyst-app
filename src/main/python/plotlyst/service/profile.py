"""
Plotlyst
Copyright (C) 2021-2025  Zsolt Kovari

This file is part of Plotlyst.

Plotlyst is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Plotlyst is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import hashlib
import logging
import os
from types import MappingProxyType

import cbor2
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding

from plotlyst.env import app_env
from plotlyst.resources import resource_registry


def verify_profile() -> bool:
    if not os.path.exists(resource_registry.profile) or not os.path.exists(
            resource_registry.public_key) or not os.path.exists(resource_registry.signature):
        return False

    with open(resource_registry.profile, "rb") as f:
        data_cbor = f.read()

    with open(resource_registry.signature, "rb") as f:
        signature = f.read()

    with open(resource_registry.public_key, "rb") as key_file:
        public_key = serialization.load_pem_public_key(key_file.read())

    data_hash = hashlib.sha256(data_cbor).digest()
    try:
        public_key.verify(
            signature,
            data_hash,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        cbor_data = cbor2.loads(data_cbor)
        app_env.setProfile(MappingProxyType(cbor_data))
        return True
    except Exception as e:
        logging.error('The signature does not match.', e)
        return False
