import os
from typing import BinaryIO
import regex as re

def find_chunk_boundaries(
    file: BinaryIO, 
    desired_num_chunks: int, 
    split_special_token: bytes
) -> list[int]:
    """
    Chunk the file into parts that can be counted independently.
    May return fewer chunks if the boundaries end up overlapping.
    """
    assert isinstance(split_special_token, bytes), (
        "Must represent special token as a bytestring"
    )

    # Get total file size in bytes
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)

    chunk_size = file_size // desired_num_chunks

    # Initial guesses for chunk boundary locations, uniformly spaced
    # Chunks start on previous index, don't include last index
    chunk_boundaries = [i * chunk_size for i in range(desired_num_chunks + 1)]
    chunk_boundaries[-1] = file_size

    mini_chunk_size = 4096  # Read ahead by 4k bytes at a time

    for bi in range(1, len(chunk_boundaries) - 1):
        initial_position = chunk_boundaries[bi]
        file.seek(initial_position)  # Start at boundary guess
        while True:
            mini_chunk = file.read(mini_chunk_size)  # Read a mini chunk

            # If EOF, this boundary should be at the end of the file
            if mini_chunk == b"":
                chunk_boundaries[bi] = file_size
                break

            # Find the special token in the mini chunk
            found_at = mini_chunk.find(split_special_token)
            if found_at != -1:
                chunk_boundaries[bi] = initial_position + found_at
                break
            initial_position += mini_chunk_size

    # Make sure all boundaries are unique, but might be fewer than desired_num_chunks
    return sorted(set(chunk_boundaries))

def pretokenize_chunk(chunk):
    """
    Pre-tokenize a chunk of text and return the token frequencies.
    This function can be parallelized by sending each chunk to a separate process.
    """
    PAT = r"""'(?:[sdmt]|ll|ve|re)| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+"""
    tokens = re.findall(PAT, chunk)
    
    # Remove whitespace from tokens
    tokens = [''.join(token.split()) for token in tokens if token not in ['\r', '\n']]
    tokens = [token for token in tokens if token]  # Remove empty strings
    
    # Count token frequencies
    dict_tokens = {tuple(token): tokens.count(token) for token in set(tokens)}
    
    return dict_tokens

def update_token_pairs(dict_tokens, token_pairs):
    # Find every successive pair and sum frequencies
    for token_tuple, count in dict_tokens.items():
        # Look at every successive pair in this token
        for idx in range(len(token_tuple) - 1):
            # Create pair from adjacent characters
            pair = (token_tuple[idx], token_tuple[idx + 1])
            # Sum the frequency of words where this pair appears
            if pair in token_pairs:
                token_pairs[pair] += count
            else:
                token_pairs[pair] = count

    # Sort pairs by frequency (descending), then lexicographically for ties
    sorted_pairs = sorted(token_pairs.items(), key=lambda x: (-x[1], x[0]))
            
    print(f"Character pairs and their frequencies (sorted):")
    for pair, freq in sorted_pairs:
        print(f"  {pair[0]}{pair[1]}: {freq}")
    
    # Find the most frequent pair (with lexicographic tiebreaker)
    if sorted_pairs:
        most_frequent_pair, highest_freq = sorted_pairs[0]
        print(f"Most frequent pair: '{most_frequent_pair[0]}{most_frequent_pair[1]}' with frequency {highest_freq}")
        print()
    

## Usage
def pretokenize_file(filepath: str, num_processes: int):
    PAT = r"""'(?:[sdmt]|ll|ve|re)| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+"""
    token_pairs = {}
    with open(filepath, "rb") as f:
        boundaries = find_chunk_boundaries(
            f, num_processes, "<|endoftext|>".encode("utf-8"))
        print(f"Chunk boundaries: {boundaries}")
            
        # The following is a serial implementation, but you can parallelize this 
        # by sending each start/end pair to a set of processes.
        for start, end in zip(boundaries[:-1], boundaries[1:]):
            f.seek(start)
            chunk = f.read(end - start).decode("utf-8", errors="ignore")

            # Run pre-tokenization on your chunk and store the counts for each pre-token
            dict_tokens = pretokenize_chunk(chunk)
            print(f"Token frequencies: {dict_tokens}")

            update_token_pairs(dict_tokens, token_pairs)
            
            

if __name__ == "__main__":
    pretokenize_file("sample_corpus.txt", num_processes=4)