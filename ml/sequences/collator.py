"""Batch collation: left-pad variable-length sequences and build attention masks (§7).

Left padding keeps the most recent week as the LAST step of every sequence,
which is what the attention-pooling head weights most heavily.
"""
import torch

from ml.config import SEQUENCE_LENGTH


class SequenceCollator:
    """Pads sequences/masks in a batch to a fixed length (SEQUENCE_LENGTH)."""

    def __init__(self, max_length: int = SEQUENCE_LENGTH):
        self.max_length = max_length

    def __call__(self, batch: list[dict]) -> dict[str, torch.Tensor]:
        seqs, masks = [], []
        for item in batch:
            seq, mask = item["sequence"], item["mask"]
            t = seq.shape[0]
            if t < self.max_length:
                pad = self.max_length - t
                seq = torch.cat([torch.zeros(pad, seq.shape[1], dtype=seq.dtype), seq], dim=0)
                mask = torch.cat([torch.zeros(pad, dtype=mask.dtype), mask], dim=0)
            elif t > self.max_length:
                seq = seq[-self.max_length:]
                mask = mask[-self.max_length:]
            seqs.append(seq)
            masks.append(mask)

        stacked_seq = torch.stack(seqs)
        stacked_mask = torch.stack(masks)
        return {
            "sequence": stacked_seq,
            "mask": stacked_mask,
            # key padding mask for nn.TransformerEncoder: True where PADDED
            "src_key_padding_mask": stacked_mask < 0.5,
            "tabular": torch.stack([item["tabular"] for item in batch]),
            "y_regression": torch.stack([item["y_regression"] for item in batch]),
            "y_classification": torch.stack([item["y_classification"] for item in batch]),
        }
