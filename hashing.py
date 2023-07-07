import hashlib
class Hashing:
    #def __init__(self,salt):
        #self.salt=salt
    def __init__(self):
        self.salt="ServerPasswordSalt1234"#Please Change
    def hash(self,data):
        hasher = hashlib.sha512()
        value = data + self.salt
        hasher.update(value.encode("utf-8"))
        hashed = hasher.hexdigest()
        #print(hashlib.algorithms_available)
        #print(hashlib.algorithms_guaranteed)
        return hashed
    def check(self,original,correct):
        hasher = hashlib.sha512()
        value = original + self.salt
        hasher.update(value.encode("utf-8"))
        hashed = hasher.hexdigest()
        print(hashed)
        print(correct)
        return hashed == correct
