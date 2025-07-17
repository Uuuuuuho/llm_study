import os
from typing import BinaryIO
import regex as re
import pdb

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

def merge_pair(token_dict, pair_to_merge):
    """
    Merge the specified pair in all tokens and return updated token dictionary.
    """
    new_token_dict = {}
    
    for token_tuple, count in token_dict.items():
        new_token = []
        i = 0
        while i < len(token_tuple):
            # Check if current position and next form the pair to merge
            if i < len(token_tuple) - 1 and (token_tuple[i], token_tuple[i + 1]) == pair_to_merge:
                # Merge the pair into a single token
                merged = token_tuple[i] + token_tuple[i + 1]
                new_token.append(merged)
                i += 2  # Skip next character since it's merged
            else:
                new_token.append(token_tuple[i])
                i += 1
        
        new_token_tuple = tuple(new_token)
        new_token_dict[new_token_tuple] = count
    
    return new_token_dict

def sort_key_function(item):
    """
    Custom sorting key function for BPE pairs.
    Returns tuple for sorting: (negative_frequency, reversed_pair_for_lexicographic_descending)
    """
    pair, frequency = item
    char1, char2 = pair
    # Use tuple reversal for descending lexicographic order
    # This works even when char1 or char2 are multi-character strings from previous merges
    return (-frequency, -ord(char1[0]), -ord(char2[0]))

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

    # Sort pairs by frequency (descending), then lexicographically DESCENDING for ties
    sorted_pairs = sorted(token_pairs.items(), key=sort_key_function)

    # Find the most frequent pair (with lexicographic tiebreaker)
    most_frequent_pair, highest_freq = sorted_pairs[0]
    return most_frequent_pair

## Usage
def pretokenize_file(filepath: str, num_processes: int):
    

    with open(filepath, "rb") as f:
        boundaries = find_chunk_boundaries(
            f, num_processes, "<|endoftext|>".encode("utf-8"))
        print(f"Chunk boundaries: {boundaries}")
            
        # The following is a serial implementation, but you can parallelize this 
        # by sending each start/end pair to a set of processes.
        for start, end in zip(boundaries[:-1], boundaries[1:]):
            f.seek(start)
            chunk = f.read(end - start).decode("utf-8", errors="ignore")
            
            # Run pre-tokenization on the given chunk
            dict_tokens = pretokenize_chunk(chunk)
            print(f"dict_tokens: {dict_tokens}")

            # Apply update & merge
            for _ in range(6):
                token_pairs = {}
                most_frequent_pair = update_token_pairs(dict_tokens, token_pairs)
                dict_tokens = merge_pair(dict_tokens, most_frequent_pair)
                print(f"Most frequent pair: {most_frequent_pair}")
            print(f"dict_tokens: {dict_tokens}")



if __name__ == "__main__":
    pretokenize_file("sample_corpus.txt", num_processes=4)