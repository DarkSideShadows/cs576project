import datetime
from blockchain.block import Block
        

class Blockchain:
    
    def __init__(self, difficulty=2):
        self.chain = [self.genesis_block()]   # chain starts with 1 block
        self.difficulty = difficulty


    # create genesis block of the blockchain
    def genesis_block(self):
        return Block(0, 
                     datetime.datetime.now(), 
                     ["Genesis Block"], 
                     "0")    
    
    
    # create a new block using the latest message
    def mine_block(self, message, timestamp):
        new_block = Block(self.get_previous_block.index + 1,
                          timestamp,
                          message,
                          self.get_previous_block.hash())
        
        new_block.proof_of_work(self.difficulty)
        return self.add_block(new_block)
    
    
    # adds a block to the chain after checking validity
    def add_block(self, new_block):
        # check that block's previous hash recorded matches the actual previous hash
        previous_block = self.get_previous_block()
        if new_block.block_content['prev_hash'] != previous_block.hash():
            print("Block rejected: Previous hash mismatch.")   # DEBUG
            return False
        
        # check that block's proof of work is correct
        if not self.is_valid(new_block):
            print("Block rejected: Invalid proof of work.")   # DEBUG
            return False
        
        # add block to chain only if both checks pass
        self.chain.append(new_block)
        return True
    
    
    # checks a block's proof of work
    def is_valid(self, block):
        target = '0' * self.difficulty
        return block.hash().startswith(target)
        
    
    def get_previous_block(self):
        return self.chain[-1]
    
    def get_length(self):
        return len(self.chain)
    
    
    # checks that the entire chain contains valid blocks
    def is_valid_chain(self):
        for i in range(1, self.get_length()):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]
            
            # perform 2 checks like in add_block
            if current_block.block_content['prev_hash'] != previous_block.hash():
                print(f"Chain invalid: Block {current_block.block_content['index']} previous hash mismatch.")   # DEBUG
                return False
            if not self.is_valid(current_block):
                print(f"Chain invalid: Block {current_block.block_content['index']} has invalid proof of work.")   # DEBUG
                return False
            
        print("Blockchain is valid")   # DEBUG
        return True
            
                
            
    
