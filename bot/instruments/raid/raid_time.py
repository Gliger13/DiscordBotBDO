import datetime
from datetime import datetime, timedelta


class RaidTime:
    DISPLAY_FREQUENCY = 4  # times
    NOTIFY_BEFORE_LEAVING = timedelta(minutes=7)
    # Display n minutes before leaving
    DISPLAY_BEFORE_LEAVING = [
        timedelta(minutes=15),
        timedelta(minutes=5),
    ]
    MIN_TIME_DISPLAY = timedelta(seconds=60)

    def __init__(self, time_leaving, time_reservation_open):
        self.creation_time = datetime.now()
        self.time_to_display = []
        self.secs_to_display = []
        self.time_leaving = time_leaving
        self.time_reservation_open = time_reservation_open

        self.notification_task = None
        self.is_notified = False  # Have users received an notification?

        self._time_leaving = datetime.strptime(time_leaving, '%H:%M')
        self._time_reservation_open = datetime.strptime(time_reservation_open, '%H:%M')

        self._set_intervals()

    @property
    def _additional_time(self):
        if self.DISPLAY_BEFORE_LEAVING:
            time_list = list(reversed(sorted(self.DISPLAY_BEFORE_LEAVING)))
            last_time = time_list.pop(0)
            time_before_next = []
            for current_time in time_list:
                time_before_next.append(last_time - current_time)
                last_time = current_time
            time_before_next.append(last_time)
            return time_before_next
        else:
            return []

    @staticmethod
    def _clear_additional_time(time_list, interval_part):
        """
        Remove time from time_list that greater than interval_part
        """
        return [time for time in time_list if time < interval_part]

    @property
    def next_time_to_display(self):
        return self.time_to_display[0]

    def secs_left_to_display(self):
        hours_end, minutes_end = tuple(map(int, self.time_to_display[0].split(':')))
        time_start = datetime.now()
        delta_start = timedelta(hours=time_start.hour, minutes=time_start.minute, seconds=time_start.second)
        delta_end = timedelta(hours=hours_end, minutes=minutes_end)
        delta_left = delta_end - delta_start
        return delta_left.seconds

    def time_passed(self):
        self.time_to_display.pop(0)

    def make_time_list(self):
        # Convert in timedelta
        time_list = []
        last_time = datetime.strptime(self.time_to_display[0], '%H:%M')
        last_time = timedelta(hours=last_time.hour, minutes=last_time.minute)
        for time_index, time in enumerate(self.time_to_display[1:]):
            time = datetime.strptime(time, '%H:%M')
            time = timedelta(hours=time.hour, minutes=time.minute)

            if time < last_time:
                for next_day_time in self.time_to_display[time_index + 1:]:
                    some_time = datetime.strptime(next_day_time, '%H:%M')
                    some_time = timedelta(hours=some_time.hour, minutes=some_time.minute)
                    time_list.append(some_time + timedelta(days=1))
                break
            else:
                time_list.append(time)

            last_time = time
        return time_list

    def validate_time(self):
        # Convert in timedelta
        time_list = self.make_time_list()

        current_datetime = datetime.now()
        current_time = timedelta(hours=current_datetime.hour, minutes=current_datetime.minute)

        if current_time < timedelta(hours=self._time_reservation_open.hour, minutes=self._time_reservation_open.minute):
            current_time += timedelta(days=1)

        for time_index, time in enumerate(time_list):
            if current_time < time:
                self.time_to_display = self.time_to_display[time_index:]
                return

    def _set_intervals(self):
        display_frequency = self.DISPLAY_FREQUENCY

        # Correct the time if the time leaving is the next day
        if self._time_reservation_open > self._time_leaving:
            interval = self._time_leaving + timedelta(days=1) - self._time_reservation_open
        else:
            interval = self._time_leaving - self._time_reservation_open

        # Reduce the frequency of display if the interval is not enough
        if interval < self.MIN_TIME_DISPLAY * display_frequency:
            display_frequency = interval // self.MIN_TIME_DISPLAY // 2

        interval_part = interval / display_frequency if display_frequency else interval
        # Take time for a specific display
        additional_list = self._clear_additional_time(self._additional_time, interval_part)

        # Calculate min_interval
        # 1 minute for compensate the time spent on computing
        min_interval = self.MIN_TIME_DISPLAY * display_frequency + timedelta(minutes=1)

        for display_time in additional_list:
            min_interval += display_time

        # do not display if the interval is small
        if interval > min_interval and additional_list and interval_part > max(additional_list):
            can_additionally_display = True
            interval -= max(additional_list)
        else:
            can_additionally_display = False

        interval_part = interval / display_frequency if display_frequency else interval

        # Structure of all time interval like this
        # [__.__, __.__, __.__, __.__, *additional_time, _time_leaving]
        # where . is time to display

        self.secs_to_display.append((interval_part // 2).total_seconds())
        for part in range(display_frequency - 1):
            self.secs_to_display.append(interval_part.total_seconds())
        self.secs_to_display.append((interval_part // 2).total_seconds())

        time_to_display = self._time_reservation_open
        for interval_part_secs in self.secs_to_display:
            time_to_display += timedelta(seconds=interval_part_secs)
            str_time = time_to_display.strftime('%H:%M')
            self.time_to_display.append(str_time)

        # Add additional time to display
        if can_additionally_display:
            for additional_time in additional_list:
                time_to_display = self._time_leaving - additional_time
                str_time = time_to_display.strftime('%H:%M')
                self.time_to_display.append(str_time)
                self.secs_to_display.append(additional_time.total_seconds())

        # Add display at time leaving
        self.time_to_display.append(self._time_leaving.strftime('%H:%M'))
        # Remove duplicate items from list
        self.time_to_display = list(dict.fromkeys(self.time_to_display))

    def secs_to_notify(self) -> float or None:
        if not self.is_notified:
            time_leaving = timedelta(hours=self._time_leaving.hour, minutes=self._time_leaving.minute)
            current_time = datetime.now()
            current_time = timedelta(hours=current_time.hour, minutes=current_time.minute)
            if current_time > time_leaving:
                time_leaving += timedelta(days=1)
            secs_left_to_notify = (time_leaving - current_time - self.NOTIFY_BEFORE_LEAVING).total_seconds()
            if secs_left_to_notify < 0:
                return
            else:
                return secs_left_to_notify
