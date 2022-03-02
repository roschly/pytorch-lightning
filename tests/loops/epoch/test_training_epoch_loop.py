# Copyright The PyTorch Lightning team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from unittest import mock
from unittest.mock import Mock, patch

import pytest

from pytorch_lightning.loops import TrainingEpochLoop
from pytorch_lightning.loops.epoch.training_epoch_loop import _v1_8_output_format
from pytorch_lightning.trainer.trainer import Trainer
from tests.deprecated_api import no_deprecated_call
from tests.helpers.boring_model import BoringModel

_out00 = {"loss": 0.0}
_out01 = {"loss": 0.1}
_out02 = {"loss": 0.2}
_out03 = {"loss": 0.3}
_out10 = {"loss": 1.0}
_out11 = {"loss": 1.1}
_out12 = {"loss": 1.2}
_out13 = {"loss": 1.3}


@pytest.mark.parametrize(
    "num_optimizers,tbptt_splits,batch_outputs,expected",
    [
        (1, 0, [], []),
        (1, 0, [[]], []),
        # 1 batch
        (1, 0, [[{0: _out00}]], [_out00]),
        # 2 batches
        (1, 0, [[{0: _out00}], [{0: _out01}]], [_out00, _out01]),
        # 1 batch, 2 optimizers
        (2, 0, [[{0: _out00, 1: _out01}]], [_out00, _out01]),
        # 2 batches, 2 optimizers
        (
            2,
            0,
            [[{0: _out00, 1: _out01}], [{0: _out10, 1: _out11}]],
            [[_out00, _out01], [_out10, _out11]],
        ),
        # 4 batches, 2 optimizers, different frequency
        (
            2,
            0,
            [[{0: _out00}], [{1: _out01}], [{1: _out11}], [{0: _out10}]],
            [[_out00], [_out01], [_out11], [_out10]],
        ),
        # 1 batch, tbptt with 2 splits (uneven)
        (1, 2, [[{0: _out00}, {0: _out01}], [{0: _out03}]], [[_out00, _out01], [_out03]]),
        # 3 batches, tbptt with 2 splits, 2 optimizers alternating
        (
            2,
            2,
            [[{0: _out00}, {0: _out01}], [{1: _out10}, {1: _out11}], [{0: _out02}, {0: _out03}]],
            [[[_out00, _out01], [], [_out02, _out03]], [[], [_out10, _out11], []]],
        ),
    ],
)
def test_prepare_outputs_training_epoch_end_automatic_old_format(num_optimizers, tbptt_splits, batch_outputs, expected):
    """Test that the loop converts the nested lists of outputs to the format that the `training_epoch_end` hook
    currently expects in the case of automatic optimization."""
    lightning_module = Mock()
    lightning_module.automatic_optimization = True
    lightning_module.truncated_bptt_steps = tbptt_splits
    match = "will change in version v1.8.*new_format=True"
    ctx_manager = pytest.deprecated_call if tbptt_splits and num_optimizers > 1 else no_deprecated_call
    with ctx_manager(match=match):
        with mock.patch("pytorch_lightning.loops.epoch.training_epoch_loop._v1_8_output_format", return_value=False):
            prepared = TrainingEpochLoop._prepare_outputs_training_epoch_end(
                batch_outputs,
                lightning_module=lightning_module,
                num_optimizers=num_optimizers,  # does not matter for manual optimization
            )
    assert prepared == expected


@pytest.mark.parametrize(
    "batch_outputs,expected",
    [
        ([], []),
        ([[]], []),
        # 1 batch
        ([[_out00]], [_out00]),
        # 2 batches
        ([[_out00], [_out01]], [_out00, _out01]),
        # skipped outputs
        ([[_out00], [], [], [_out03]], [_out00, _out03]),
        # tbptt with 2 splits, uneven, skipped output
        ([[_out00, _out01], [_out02, _out03], [], [_out10]], [[_out00, _out01], [_out02, _out03], [_out10]]),
    ],
)
def test_prepare_outputs_training_epoch_end_manual(batch_outputs, expected):
    """Test that the loop converts the nested lists of outputs to the format that the `training_epoch_end` hook
    currently expects in the case of manual optimization."""
    lightning_module = Mock()
    lightning_module.automatic_optimization = False
    with mock.patch("pytorch_lightning.loops.epoch.training_epoch_loop._v1_8_output_format", return_value=False):
        prepared = TrainingEpochLoop._prepare_outputs_training_epoch_end(
            batch_outputs,
            lightning_module=lightning_module,
            num_optimizers=-1,  # does not matter for manual optimization
        )
    assert prepared == expected


@pytest.mark.parametrize(
    "num_optimizers,tbptt_splits,batch_end_outputs,expected",
    [
        (1, 0, [], []),
        (1, 0, [[]], []),
        (1, 0, [{0: _out00}], _out00),
        (2, 0, [{0: _out00, 1: _out01}], [_out00, _out01]),
        (1, 2, [{0: _out00}, {0: _out01}], [_out00, _out01]),
        (2, 2, [{0: _out00, 1: _out01}, {0: _out10, 1: _out11}], [[_out00, _out10], [_out01, _out11]]),
    ],
)
def test_prepare_outputs_training_batch_end_automatic_old_format(
    num_optimizers, tbptt_splits, batch_end_outputs, expected
):
    """Test that the loop converts the nested lists of outputs to the format that the `on_train_batch_end` hook
    currently expects in the case of automatic optimization."""
    lightning_module = Mock()
    lightning_module.automatic_optimization = True
    lightning_module.truncated_bptt_steps = tbptt_splits
    match = "will change in version v1.8.*new_format=True"
    ctx_manager = pytest.deprecated_call if tbptt_splits and num_optimizers > 1 else no_deprecated_call
    with ctx_manager(match=match):
        with mock.patch("pytorch_lightning.loops.epoch.training_epoch_loop._v1_8_output_format", return_value=False):
            prepared = TrainingEpochLoop._prepare_outputs_training_batch_end(
                batch_end_outputs,
                lightning_module=lightning_module,
                num_optimizers=num_optimizers,
            )
    assert prepared == expected


@pytest.mark.parametrize(
    "batch_end_outputs,expected",
    [
        ([], []),
        ([[]], []),
        # skipped outputs
        ([_out00, None, _out02], [_out00, _out02]),
        # tbptt with 3 splits, skipped output
        ([_out00, _out01, None, _out03], [_out00, _out01, _out03]),
    ],
)
def test_prepare_outputs_training_batch_end_manual(batch_end_outputs, expected):
    """Test that the loop converts the nested lists of outputs to the format that the `on_train_batch_end` hook
    currently expects in the case of manual optimization."""
    lightning_module = Mock()
    lightning_module.automatic_optimization = False
    with mock.patch("pytorch_lightning.loops.epoch.training_epoch_loop._v1_8_output_format", return_value=False):
        prepared = TrainingEpochLoop._prepare_outputs_training_batch_end(
            batch_end_outputs,
            lightning_module=lightning_module,
            num_optimizers=-1,  # does not matter for manual optimization
        )
    assert prepared == expected


def test_no_val_on_train_epoch_loop_restart(tmpdir):
    """Test that training validation loop doesn't get triggered at the beginning of a restart."""
    trainer_kwargs = {
        "max_epochs": 1,
        "limit_train_batches": 1,
        "limit_val_batches": 1,
        "num_sanity_val_steps": 0,
        "enable_checkpointing": False,
    }
    trainer = Trainer(**trainer_kwargs)
    model = BoringModel()
    trainer.fit(model)
    ckpt_path = str(tmpdir / "last.ckpt")
    trainer.save_checkpoint(ckpt_path)

    trainer_kwargs["max_epochs"] = 2
    trainer = Trainer(**trainer_kwargs)

    with patch.object(
        trainer.fit_loop.epoch_loop.val_loop, "advance", wraps=trainer.fit_loop.epoch_loop.val_loop.advance
    ) as advance_mocked:
        trainer.fit(model, ckpt_path=ckpt_path)
        assert advance_mocked.call_count == 1


def test_v1_8_output_format():
    # old format
    def training_epoch_end(outputs):
        ...

    assert not _v1_8_output_format(training_epoch_end)

    def training_epoch_end(outputs, new_format=1):
        ...

    assert not _v1_8_output_format(training_epoch_end)

    def training_epoch_end(outputs, new_format=False):
        ...

    assert not _v1_8_output_format(training_epoch_end)

    # new format
    def training_epoch_end(outputs, new_format=True):
        ...

    assert _v1_8_output_format(training_epoch_end)
