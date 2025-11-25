class SlotNotOpenError(Exception):
    pass


class DuplicateReservationError(Exception):
    pass


class CapacityError(Exception):
    pass


class VersionConflictError(Exception):
    pass
