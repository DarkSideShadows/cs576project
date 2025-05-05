# block implementation for blockchain
import hashlib
import json


class Block:
    
    # store contents of block in json format
    def __init__(self, index, timestamp, message, prev_hash, nonce=0):
        self.block_content = {
            'index': index,
            'timestamp': timestamp,
            'message': message,
            'prev_hash': prev_hash,
            'nonce': nonce
        }
        self.nonce = nonce
        
        
    # get the hash value of the block
    def hash(self):
        self.block_content['nonce'] = self.nonce   # update nonce value
        encoded_block = json.dumps(self.block_content, sort_keys=True).encode()
        return hashlib.sha256(encoded_block).hexdigest()
    
    
    # continually hash the contents of the block until hash begins with difficulty 0s
    # returns nonce value used for validity checking by other peers
    def proof_of_work(self, difficulty):
        target = '0' * difficulty
        while not self.hash().startswith(target):
            self.nonce += 1   # increment nonce value
        return self.nonce