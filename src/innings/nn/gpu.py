"""The served network, loaded back into PyTorch so that a graphics card can run it.

The site keeps one copy of the trained network: the exported file that onnxruntime runs on a
CPU. Simulating a season needs millions of balls at once, which is a graphics card's job, so
this module rebuilds the PyTorch model from that same file. One network, two ways to run it.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import onnx
import torch
from onnx import numpy_helper

from .model import BallModel, ModelConfig
from .serve import FOLDER

EXPORT_PREFIX = "model."


def _gru_weights(node: onnx.NodeProto, exported: dict[str, np.ndarray], hidden: int) -> dict:
    """The recurrent layer's weights, in PyTorch's order.

    The exported file stores a GRU's three gates as (update, reset, new). PyTorch wants
    (reset, update, new), so the first two blocks of every weight swap places.
    """
    def reordered(weights: np.ndarray) -> torch.Tensor:
        update, reset, new = np.split(weights, 3, axis=0)
        return torch.from_numpy(np.concatenate([reset, update, new], axis=0).copy())

    from_input, from_hidden, biases = (exported[name][0] for name in node.input[1:4])
    return {"recent.weight_ih_l0": reordered(from_input), "recent.weight_hh_l0": reordered(from_hidden),
            "recent.bias_ih_l0": reordered(biases[:3 * hidden]),
            "recent.bias_hh_l0": reordered(biases[3 * hidden:])}


def load(folder: Path = FOLDER, device: str = "cuda") -> tuple[BallModel, dict]:
    """The deployed network on `device`, ready to predict, and the ids it knows."""
    graph = onnx.load(str(folder / "model.onnx")).graph
    exported = {tensor.name: numpy_helper.to_array(tensor) for tensor in graph.initializer}
    weights = {name.removeprefix(EXPORT_PREFIX): torch.from_numpy(values.copy())
               for name, values in exported.items() if name.startswith(EXPORT_PREFIX)}
    sizes = {kind: weights[f"{kind[:-1]}.weight"].shape[0]
             for kind in ("batters", "bowlers", "venues", "leagues")}
    config = ModelConfig(**sizes)
    weights |= _gru_weights(next(node for node in graph.node if node.op_type == "GRU"),
                            exported, config.history_dim)
    model = BallModel(config)
    model.load_state_dict(weights)
    vocabulary = json.loads((folder / "vocabulary.json").read_text())
    return model.to(device).eval(), vocabulary
