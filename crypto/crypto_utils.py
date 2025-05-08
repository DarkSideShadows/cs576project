# crypto_utils.py

# this module handles all cryptographic operations:
    # -RSA key generation
    # -public key serialization/deserialization
    # -message encryption/decryption

from cryptography.hazmat.primitives.asymmetric import rsa, padding # type: ignore
from cryptography.hazmat.primitives import serialization, hashes # type: ignore

# generate a new RSA key pair (private + public)
def generate_key_pair():
    # 2048-bit RSA
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    return private_key, private_key.public_key()

# convert public key to bytes (PEM format) for sending over the network
def serialize_public_key(public_key):
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

# Turn received bytes into a public key object
def deserialize_public_key(pubkey_bytes):
    return serialization.load_pem_public_key(pubkey_bytes)

# Encrypt a message using the peer's public key
def encrypt_message(public_key, message):
    return public_key.encrypt(
        message.encode(), # convert string to bytes
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()), # mask generation function
            algorithm=hashes.SHA256(), # hash function
            label=None
        )
    )

# Decrypt a message (bytes) using your private key
def decrypt_message(private_key, ciphertext):
    return private_key.decrypt(
        ciphertext,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    ).decode() # convert bytes back to string