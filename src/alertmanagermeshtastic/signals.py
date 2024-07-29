"""
alertmanagermeshtastic.signals
~~~~~~~~~~~~~~~~~~~

Signals

:Copyright: 2007-2022 Jochen Kupperschmidt
:Copyright: 2023 Alexander Volz
:License: MIT, see LICENSE for details.
"""

from blinker import Signal


message_received = Signal()
queue_size_updated = Signal('queue_size')
meshtastic_connected = Signal('meshtastic_connected')
clear_queue_issued = Signal('clear_queue_issued')
