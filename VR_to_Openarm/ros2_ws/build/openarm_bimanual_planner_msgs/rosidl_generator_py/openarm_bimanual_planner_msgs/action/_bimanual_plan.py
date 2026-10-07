# generated from rosidl_generator_py/resource/_idl.py.em
# with input from openarm_bimanual_planner_msgs:action/BimanualPlan.idl
# generated code does not contain a copyright notice


# Import statements for member types

import builtins  # noqa: E402, I100

import math  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_BimanualPlan_Goal(type):
    """Metaclass of message 'BimanualPlan_Goal'."""

    _CREATE_ROS_MESSAGE = None
    _CONVERT_FROM_PY = None
    _CONVERT_TO_PY = None
    _DESTROY_ROS_MESSAGE = None
    _TYPE_SUPPORT = None

    __constants = {
    }

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('openarm_bimanual_planner_msgs')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'openarm_bimanual_planner_msgs.action.BimanualPlan_Goal')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__action__bimanual_plan__goal
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__action__bimanual_plan__goal
            cls._CONVERT_TO_PY = module.convert_to_py_msg__action__bimanual_plan__goal
            cls._TYPE_SUPPORT = module.type_support_msg__action__bimanual_plan__goal
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__action__bimanual_plan__goal

            from geometry_msgs.msg import Pose
            if Pose.__class__._TYPE_SUPPORT is None:
                Pose.__class__.__import_type_support__()

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class BimanualPlan_Goal(metaclass=Metaclass_BimanualPlan_Goal):
    """Message class 'BimanualPlan_Goal'."""

    __slots__ = [
        '_left_ee_pose',
        '_right_ee_pose',
        '_duration',
    ]

    _fields_and_field_types = {
        'left_ee_pose': 'geometry_msgs/Pose',
        'right_ee_pose': 'geometry_msgs/Pose',
        'duration': 'double',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.NamespacedType(['geometry_msgs', 'msg'], 'Pose'),  # noqa: E501
        rosidl_parser.definition.NamespacedType(['geometry_msgs', 'msg'], 'Pose'),  # noqa: E501
        rosidl_parser.definition.BasicType('double'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        from geometry_msgs.msg import Pose
        self.left_ee_pose = kwargs.get('left_ee_pose', Pose())
        from geometry_msgs.msg import Pose
        self.right_ee_pose = kwargs.get('right_ee_pose', Pose())
        self.duration = kwargs.get('duration', float())

    def __repr__(self):
        typename = self.__class__.__module__.split('.')
        typename.pop()
        typename.append(self.__class__.__name__)
        args = []
        for s, t in zip(self.__slots__, self.SLOT_TYPES):
            field = getattr(self, s)
            fieldstr = repr(field)
            # We use Python array type for fields that can be directly stored
            # in them, and "normal" sequences for everything else.  If it is
            # a type that we store in an array, strip off the 'array' portion.
            if (
                isinstance(t, rosidl_parser.definition.AbstractSequence) and
                isinstance(t.value_type, rosidl_parser.definition.BasicType) and
                t.value_type.typename in ['float', 'double', 'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64']
            ):
                if len(field) == 0:
                    fieldstr = '[]'
                else:
                    assert fieldstr.startswith('array(')
                    prefix = "array('X', "
                    suffix = ')'
                    fieldstr = fieldstr[len(prefix):-len(suffix)]
            args.append(s[1:] + '=' + fieldstr)
        return '%s(%s)' % ('.'.join(typename), ', '.join(args))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.left_ee_pose != other.left_ee_pose:
            return False
        if self.right_ee_pose != other.right_ee_pose:
            return False
        if self.duration != other.duration:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def left_ee_pose(self):
        """Message field 'left_ee_pose'."""
        return self._left_ee_pose

    @left_ee_pose.setter
    def left_ee_pose(self, value):
        if __debug__:
            from geometry_msgs.msg import Pose
            assert \
                isinstance(value, Pose), \
                "The 'left_ee_pose' field must be a sub message of type 'Pose'"
        self._left_ee_pose = value

    @builtins.property
    def right_ee_pose(self):
        """Message field 'right_ee_pose'."""
        return self._right_ee_pose

    @right_ee_pose.setter
    def right_ee_pose(self, value):
        if __debug__:
            from geometry_msgs.msg import Pose
            assert \
                isinstance(value, Pose), \
                "The 'right_ee_pose' field must be a sub message of type 'Pose'"
        self._right_ee_pose = value

    @builtins.property
    def duration(self):
        """Message field 'duration'."""
        return self._duration

    @duration.setter
    def duration(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'duration' field must be of type 'float'"
            assert not (value < -1.7976931348623157e+308 or value > 1.7976931348623157e+308) or math.isinf(value), \
                "The 'duration' field must be a double in [-1.7976931348623157e+308, 1.7976931348623157e+308]"
        self._duration = value


# Import statements for member types

# already imported above
# import builtins

# already imported above
# import rosidl_parser.definition


class Metaclass_BimanualPlan_Result(type):
    """Metaclass of message 'BimanualPlan_Result'."""

    _CREATE_ROS_MESSAGE = None
    _CONVERT_FROM_PY = None
    _CONVERT_TO_PY = None
    _DESTROY_ROS_MESSAGE = None
    _TYPE_SUPPORT = None

    __constants = {
    }

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('openarm_bimanual_planner_msgs')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'openarm_bimanual_planner_msgs.action.BimanualPlan_Result')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__action__bimanual_plan__result
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__action__bimanual_plan__result
            cls._CONVERT_TO_PY = module.convert_to_py_msg__action__bimanual_plan__result
            cls._TYPE_SUPPORT = module.type_support_msg__action__bimanual_plan__result
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__action__bimanual_plan__result

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class BimanualPlan_Result(metaclass=Metaclass_BimanualPlan_Result):
    """Message class 'BimanualPlan_Result'."""

    __slots__ = [
        '_success',
        '_message',
    ]

    _fields_and_field_types = {
        'success': 'boolean',
        'message': 'string',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.BasicType('boolean'),  # noqa: E501
        rosidl_parser.definition.UnboundedString(),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.success = kwargs.get('success', bool())
        self.message = kwargs.get('message', str())

    def __repr__(self):
        typename = self.__class__.__module__.split('.')
        typename.pop()
        typename.append(self.__class__.__name__)
        args = []
        for s, t in zip(self.__slots__, self.SLOT_TYPES):
            field = getattr(self, s)
            fieldstr = repr(field)
            # We use Python array type for fields that can be directly stored
            # in them, and "normal" sequences for everything else.  If it is
            # a type that we store in an array, strip off the 'array' portion.
            if (
                isinstance(t, rosidl_parser.definition.AbstractSequence) and
                isinstance(t.value_type, rosidl_parser.definition.BasicType) and
                t.value_type.typename in ['float', 'double', 'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64']
            ):
                if len(field) == 0:
                    fieldstr = '[]'
                else:
                    assert fieldstr.startswith('array(')
                    prefix = "array('X', "
                    suffix = ')'
                    fieldstr = fieldstr[len(prefix):-len(suffix)]
            args.append(s[1:] + '=' + fieldstr)
        return '%s(%s)' % ('.'.join(typename), ', '.join(args))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.success != other.success:
            return False
        if self.message != other.message:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def success(self):
        """Message field 'success'."""
        return self._success

    @success.setter
    def success(self, value):
        if __debug__:
            assert \
                isinstance(value, bool), \
                "The 'success' field must be of type 'bool'"
        self._success = value

    @builtins.property
    def message(self):
        """Message field 'message'."""
        return self._message

    @message.setter
    def message(self, value):
        if __debug__:
            assert \
                isinstance(value, str), \
                "The 'message' field must be of type 'str'"
        self._message = value


# Import statements for member types

# already imported above
# import builtins

# already imported above
# import math

# already imported above
# import rosidl_parser.definition


class Metaclass_BimanualPlan_Feedback(type):
    """Metaclass of message 'BimanualPlan_Feedback'."""

    _CREATE_ROS_MESSAGE = None
    _CONVERT_FROM_PY = None
    _CONVERT_TO_PY = None
    _DESTROY_ROS_MESSAGE = None
    _TYPE_SUPPORT = None

    __constants = {
    }

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('openarm_bimanual_planner_msgs')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'openarm_bimanual_planner_msgs.action.BimanualPlan_Feedback')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__action__bimanual_plan__feedback
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__action__bimanual_plan__feedback
            cls._CONVERT_TO_PY = module.convert_to_py_msg__action__bimanual_plan__feedback
            cls._TYPE_SUPPORT = module.type_support_msg__action__bimanual_plan__feedback
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__action__bimanual_plan__feedback

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class BimanualPlan_Feedback(metaclass=Metaclass_BimanualPlan_Feedback):
    """Message class 'BimanualPlan_Feedback'."""

    __slots__ = [
        '_progress',
    ]

    _fields_and_field_types = {
        'progress': 'float',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.progress = kwargs.get('progress', float())

    def __repr__(self):
        typename = self.__class__.__module__.split('.')
        typename.pop()
        typename.append(self.__class__.__name__)
        args = []
        for s, t in zip(self.__slots__, self.SLOT_TYPES):
            field = getattr(self, s)
            fieldstr = repr(field)
            # We use Python array type for fields that can be directly stored
            # in them, and "normal" sequences for everything else.  If it is
            # a type that we store in an array, strip off the 'array' portion.
            if (
                isinstance(t, rosidl_parser.definition.AbstractSequence) and
                isinstance(t.value_type, rosidl_parser.definition.BasicType) and
                t.value_type.typename in ['float', 'double', 'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64']
            ):
                if len(field) == 0:
                    fieldstr = '[]'
                else:
                    assert fieldstr.startswith('array(')
                    prefix = "array('X', "
                    suffix = ')'
                    fieldstr = fieldstr[len(prefix):-len(suffix)]
            args.append(s[1:] + '=' + fieldstr)
        return '%s(%s)' % ('.'.join(typename), ', '.join(args))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.progress != other.progress:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def progress(self):
        """Message field 'progress'."""
        return self._progress

    @progress.setter
    def progress(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'progress' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'progress' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._progress = value


# Import statements for member types

# already imported above
# import builtins

# already imported above
# import rosidl_parser.definition


class Metaclass_BimanualPlan_SendGoal_Request(type):
    """Metaclass of message 'BimanualPlan_SendGoal_Request'."""

    _CREATE_ROS_MESSAGE = None
    _CONVERT_FROM_PY = None
    _CONVERT_TO_PY = None
    _DESTROY_ROS_MESSAGE = None
    _TYPE_SUPPORT = None

    __constants = {
    }

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('openarm_bimanual_planner_msgs')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'openarm_bimanual_planner_msgs.action.BimanualPlan_SendGoal_Request')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__action__bimanual_plan__send_goal__request
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__action__bimanual_plan__send_goal__request
            cls._CONVERT_TO_PY = module.convert_to_py_msg__action__bimanual_plan__send_goal__request
            cls._TYPE_SUPPORT = module.type_support_msg__action__bimanual_plan__send_goal__request
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__action__bimanual_plan__send_goal__request

            from openarm_bimanual_planner_msgs.action import BimanualPlan
            if BimanualPlan.Goal.__class__._TYPE_SUPPORT is None:
                BimanualPlan.Goal.__class__.__import_type_support__()

            from unique_identifier_msgs.msg import UUID
            if UUID.__class__._TYPE_SUPPORT is None:
                UUID.__class__.__import_type_support__()

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class BimanualPlan_SendGoal_Request(metaclass=Metaclass_BimanualPlan_SendGoal_Request):
    """Message class 'BimanualPlan_SendGoal_Request'."""

    __slots__ = [
        '_goal_id',
        '_goal',
    ]

    _fields_and_field_types = {
        'goal_id': 'unique_identifier_msgs/UUID',
        'goal': 'openarm_bimanual_planner_msgs/BimanualPlan_Goal',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.NamespacedType(['unique_identifier_msgs', 'msg'], 'UUID'),  # noqa: E501
        rosidl_parser.definition.NamespacedType(['openarm_bimanual_planner_msgs', 'action'], 'BimanualPlan_Goal'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        from unique_identifier_msgs.msg import UUID
        self.goal_id = kwargs.get('goal_id', UUID())
        from openarm_bimanual_planner_msgs.action._bimanual_plan import BimanualPlan_Goal
        self.goal = kwargs.get('goal', BimanualPlan_Goal())

    def __repr__(self):
        typename = self.__class__.__module__.split('.')
        typename.pop()
        typename.append(self.__class__.__name__)
        args = []
        for s, t in zip(self.__slots__, self.SLOT_TYPES):
            field = getattr(self, s)
            fieldstr = repr(field)
            # We use Python array type for fields that can be directly stored
            # in them, and "normal" sequences for everything else.  If it is
            # a type that we store in an array, strip off the 'array' portion.
            if (
                isinstance(t, rosidl_parser.definition.AbstractSequence) and
                isinstance(t.value_type, rosidl_parser.definition.BasicType) and
                t.value_type.typename in ['float', 'double', 'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64']
            ):
                if len(field) == 0:
                    fieldstr = '[]'
                else:
                    assert fieldstr.startswith('array(')
                    prefix = "array('X', "
                    suffix = ')'
                    fieldstr = fieldstr[len(prefix):-len(suffix)]
            args.append(s[1:] + '=' + fieldstr)
        return '%s(%s)' % ('.'.join(typename), ', '.join(args))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.goal_id != other.goal_id:
            return False
        if self.goal != other.goal:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def goal_id(self):
        """Message field 'goal_id'."""
        return self._goal_id

    @goal_id.setter
    def goal_id(self, value):
        if __debug__:
            from unique_identifier_msgs.msg import UUID
            assert \
                isinstance(value, UUID), \
                "The 'goal_id' field must be a sub message of type 'UUID'"
        self._goal_id = value

    @builtins.property
    def goal(self):
        """Message field 'goal'."""
        return self._goal

    @goal.setter
    def goal(self, value):
        if __debug__:
            from openarm_bimanual_planner_msgs.action._bimanual_plan import BimanualPlan_Goal
            assert \
                isinstance(value, BimanualPlan_Goal), \
                "The 'goal' field must be a sub message of type 'BimanualPlan_Goal'"
        self._goal = value


# Import statements for member types

# already imported above
# import builtins

# already imported above
# import rosidl_parser.definition


class Metaclass_BimanualPlan_SendGoal_Response(type):
    """Metaclass of message 'BimanualPlan_SendGoal_Response'."""

    _CREATE_ROS_MESSAGE = None
    _CONVERT_FROM_PY = None
    _CONVERT_TO_PY = None
    _DESTROY_ROS_MESSAGE = None
    _TYPE_SUPPORT = None

    __constants = {
    }

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('openarm_bimanual_planner_msgs')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'openarm_bimanual_planner_msgs.action.BimanualPlan_SendGoal_Response')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__action__bimanual_plan__send_goal__response
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__action__bimanual_plan__send_goal__response
            cls._CONVERT_TO_PY = module.convert_to_py_msg__action__bimanual_plan__send_goal__response
            cls._TYPE_SUPPORT = module.type_support_msg__action__bimanual_plan__send_goal__response
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__action__bimanual_plan__send_goal__response

            from builtin_interfaces.msg import Time
            if Time.__class__._TYPE_SUPPORT is None:
                Time.__class__.__import_type_support__()

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class BimanualPlan_SendGoal_Response(metaclass=Metaclass_BimanualPlan_SendGoal_Response):
    """Message class 'BimanualPlan_SendGoal_Response'."""

    __slots__ = [
        '_accepted',
        '_stamp',
    ]

    _fields_and_field_types = {
        'accepted': 'boolean',
        'stamp': 'builtin_interfaces/Time',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.BasicType('boolean'),  # noqa: E501
        rosidl_parser.definition.NamespacedType(['builtin_interfaces', 'msg'], 'Time'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.accepted = kwargs.get('accepted', bool())
        from builtin_interfaces.msg import Time
        self.stamp = kwargs.get('stamp', Time())

    def __repr__(self):
        typename = self.__class__.__module__.split('.')
        typename.pop()
        typename.append(self.__class__.__name__)
        args = []
        for s, t in zip(self.__slots__, self.SLOT_TYPES):
            field = getattr(self, s)
            fieldstr = repr(field)
            # We use Python array type for fields that can be directly stored
            # in them, and "normal" sequences for everything else.  If it is
            # a type that we store in an array, strip off the 'array' portion.
            if (
                isinstance(t, rosidl_parser.definition.AbstractSequence) and
                isinstance(t.value_type, rosidl_parser.definition.BasicType) and
                t.value_type.typename in ['float', 'double', 'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64']
            ):
                if len(field) == 0:
                    fieldstr = '[]'
                else:
                    assert fieldstr.startswith('array(')
                    prefix = "array('X', "
                    suffix = ')'
                    fieldstr = fieldstr[len(prefix):-len(suffix)]
            args.append(s[1:] + '=' + fieldstr)
        return '%s(%s)' % ('.'.join(typename), ', '.join(args))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.accepted != other.accepted:
            return False
        if self.stamp != other.stamp:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def accepted(self):
        """Message field 'accepted'."""
        return self._accepted

    @accepted.setter
    def accepted(self, value):
        if __debug__:
            assert \
                isinstance(value, bool), \
                "The 'accepted' field must be of type 'bool'"
        self._accepted = value

    @builtins.property
    def stamp(self):
        """Message field 'stamp'."""
        return self._stamp

    @stamp.setter
    def stamp(self, value):
        if __debug__:
            from builtin_interfaces.msg import Time
            assert \
                isinstance(value, Time), \
                "The 'stamp' field must be a sub message of type 'Time'"
        self._stamp = value


class Metaclass_BimanualPlan_SendGoal(type):
    """Metaclass of service 'BimanualPlan_SendGoal'."""

    _TYPE_SUPPORT = None

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('openarm_bimanual_planner_msgs')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'openarm_bimanual_planner_msgs.action.BimanualPlan_SendGoal')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._TYPE_SUPPORT = module.type_support_srv__action__bimanual_plan__send_goal

            from openarm_bimanual_planner_msgs.action import _bimanual_plan
            if _bimanual_plan.Metaclass_BimanualPlan_SendGoal_Request._TYPE_SUPPORT is None:
                _bimanual_plan.Metaclass_BimanualPlan_SendGoal_Request.__import_type_support__()
            if _bimanual_plan.Metaclass_BimanualPlan_SendGoal_Response._TYPE_SUPPORT is None:
                _bimanual_plan.Metaclass_BimanualPlan_SendGoal_Response.__import_type_support__()


class BimanualPlan_SendGoal(metaclass=Metaclass_BimanualPlan_SendGoal):
    from openarm_bimanual_planner_msgs.action._bimanual_plan import BimanualPlan_SendGoal_Request as Request
    from openarm_bimanual_planner_msgs.action._bimanual_plan import BimanualPlan_SendGoal_Response as Response

    def __init__(self):
        raise NotImplementedError('Service classes can not be instantiated')


# Import statements for member types

# already imported above
# import builtins

# already imported above
# import rosidl_parser.definition


class Metaclass_BimanualPlan_GetResult_Request(type):
    """Metaclass of message 'BimanualPlan_GetResult_Request'."""

    _CREATE_ROS_MESSAGE = None
    _CONVERT_FROM_PY = None
    _CONVERT_TO_PY = None
    _DESTROY_ROS_MESSAGE = None
    _TYPE_SUPPORT = None

    __constants = {
    }

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('openarm_bimanual_planner_msgs')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'openarm_bimanual_planner_msgs.action.BimanualPlan_GetResult_Request')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__action__bimanual_plan__get_result__request
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__action__bimanual_plan__get_result__request
            cls._CONVERT_TO_PY = module.convert_to_py_msg__action__bimanual_plan__get_result__request
            cls._TYPE_SUPPORT = module.type_support_msg__action__bimanual_plan__get_result__request
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__action__bimanual_plan__get_result__request

            from unique_identifier_msgs.msg import UUID
            if UUID.__class__._TYPE_SUPPORT is None:
                UUID.__class__.__import_type_support__()

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class BimanualPlan_GetResult_Request(metaclass=Metaclass_BimanualPlan_GetResult_Request):
    """Message class 'BimanualPlan_GetResult_Request'."""

    __slots__ = [
        '_goal_id',
    ]

    _fields_and_field_types = {
        'goal_id': 'unique_identifier_msgs/UUID',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.NamespacedType(['unique_identifier_msgs', 'msg'], 'UUID'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        from unique_identifier_msgs.msg import UUID
        self.goal_id = kwargs.get('goal_id', UUID())

    def __repr__(self):
        typename = self.__class__.__module__.split('.')
        typename.pop()
        typename.append(self.__class__.__name__)
        args = []
        for s, t in zip(self.__slots__, self.SLOT_TYPES):
            field = getattr(self, s)
            fieldstr = repr(field)
            # We use Python array type for fields that can be directly stored
            # in them, and "normal" sequences for everything else.  If it is
            # a type that we store in an array, strip off the 'array' portion.
            if (
                isinstance(t, rosidl_parser.definition.AbstractSequence) and
                isinstance(t.value_type, rosidl_parser.definition.BasicType) and
                t.value_type.typename in ['float', 'double', 'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64']
            ):
                if len(field) == 0:
                    fieldstr = '[]'
                else:
                    assert fieldstr.startswith('array(')
                    prefix = "array('X', "
                    suffix = ')'
                    fieldstr = fieldstr[len(prefix):-len(suffix)]
            args.append(s[1:] + '=' + fieldstr)
        return '%s(%s)' % ('.'.join(typename), ', '.join(args))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.goal_id != other.goal_id:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def goal_id(self):
        """Message field 'goal_id'."""
        return self._goal_id

    @goal_id.setter
    def goal_id(self, value):
        if __debug__:
            from unique_identifier_msgs.msg import UUID
            assert \
                isinstance(value, UUID), \
                "The 'goal_id' field must be a sub message of type 'UUID'"
        self._goal_id = value


# Import statements for member types

# already imported above
# import builtins

# already imported above
# import rosidl_parser.definition


class Metaclass_BimanualPlan_GetResult_Response(type):
    """Metaclass of message 'BimanualPlan_GetResult_Response'."""

    _CREATE_ROS_MESSAGE = None
    _CONVERT_FROM_PY = None
    _CONVERT_TO_PY = None
    _DESTROY_ROS_MESSAGE = None
    _TYPE_SUPPORT = None

    __constants = {
    }

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('openarm_bimanual_planner_msgs')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'openarm_bimanual_planner_msgs.action.BimanualPlan_GetResult_Response')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__action__bimanual_plan__get_result__response
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__action__bimanual_plan__get_result__response
            cls._CONVERT_TO_PY = module.convert_to_py_msg__action__bimanual_plan__get_result__response
            cls._TYPE_SUPPORT = module.type_support_msg__action__bimanual_plan__get_result__response
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__action__bimanual_plan__get_result__response

            from openarm_bimanual_planner_msgs.action import BimanualPlan
            if BimanualPlan.Result.__class__._TYPE_SUPPORT is None:
                BimanualPlan.Result.__class__.__import_type_support__()

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class BimanualPlan_GetResult_Response(metaclass=Metaclass_BimanualPlan_GetResult_Response):
    """Message class 'BimanualPlan_GetResult_Response'."""

    __slots__ = [
        '_status',
        '_result',
    ]

    _fields_and_field_types = {
        'status': 'int8',
        'result': 'openarm_bimanual_planner_msgs/BimanualPlan_Result',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.BasicType('int8'),  # noqa: E501
        rosidl_parser.definition.NamespacedType(['openarm_bimanual_planner_msgs', 'action'], 'BimanualPlan_Result'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.status = kwargs.get('status', int())
        from openarm_bimanual_planner_msgs.action._bimanual_plan import BimanualPlan_Result
        self.result = kwargs.get('result', BimanualPlan_Result())

    def __repr__(self):
        typename = self.__class__.__module__.split('.')
        typename.pop()
        typename.append(self.__class__.__name__)
        args = []
        for s, t in zip(self.__slots__, self.SLOT_TYPES):
            field = getattr(self, s)
            fieldstr = repr(field)
            # We use Python array type for fields that can be directly stored
            # in them, and "normal" sequences for everything else.  If it is
            # a type that we store in an array, strip off the 'array' portion.
            if (
                isinstance(t, rosidl_parser.definition.AbstractSequence) and
                isinstance(t.value_type, rosidl_parser.definition.BasicType) and
                t.value_type.typename in ['float', 'double', 'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64']
            ):
                if len(field) == 0:
                    fieldstr = '[]'
                else:
                    assert fieldstr.startswith('array(')
                    prefix = "array('X', "
                    suffix = ')'
                    fieldstr = fieldstr[len(prefix):-len(suffix)]
            args.append(s[1:] + '=' + fieldstr)
        return '%s(%s)' % ('.'.join(typename), ', '.join(args))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.status != other.status:
            return False
        if self.result != other.result:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def status(self):
        """Message field 'status'."""
        return self._status

    @status.setter
    def status(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'status' field must be of type 'int'"
            assert value >= -128 and value < 128, \
                "The 'status' field must be an integer in [-128, 127]"
        self._status = value

    @builtins.property
    def result(self):
        """Message field 'result'."""
        return self._result

    @result.setter
    def result(self, value):
        if __debug__:
            from openarm_bimanual_planner_msgs.action._bimanual_plan import BimanualPlan_Result
            assert \
                isinstance(value, BimanualPlan_Result), \
                "The 'result' field must be a sub message of type 'BimanualPlan_Result'"
        self._result = value


class Metaclass_BimanualPlan_GetResult(type):
    """Metaclass of service 'BimanualPlan_GetResult'."""

    _TYPE_SUPPORT = None

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('openarm_bimanual_planner_msgs')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'openarm_bimanual_planner_msgs.action.BimanualPlan_GetResult')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._TYPE_SUPPORT = module.type_support_srv__action__bimanual_plan__get_result

            from openarm_bimanual_planner_msgs.action import _bimanual_plan
            if _bimanual_plan.Metaclass_BimanualPlan_GetResult_Request._TYPE_SUPPORT is None:
                _bimanual_plan.Metaclass_BimanualPlan_GetResult_Request.__import_type_support__()
            if _bimanual_plan.Metaclass_BimanualPlan_GetResult_Response._TYPE_SUPPORT is None:
                _bimanual_plan.Metaclass_BimanualPlan_GetResult_Response.__import_type_support__()


class BimanualPlan_GetResult(metaclass=Metaclass_BimanualPlan_GetResult):
    from openarm_bimanual_planner_msgs.action._bimanual_plan import BimanualPlan_GetResult_Request as Request
    from openarm_bimanual_planner_msgs.action._bimanual_plan import BimanualPlan_GetResult_Response as Response

    def __init__(self):
        raise NotImplementedError('Service classes can not be instantiated')


# Import statements for member types

# already imported above
# import builtins

# already imported above
# import rosidl_parser.definition


class Metaclass_BimanualPlan_FeedbackMessage(type):
    """Metaclass of message 'BimanualPlan_FeedbackMessage'."""

    _CREATE_ROS_MESSAGE = None
    _CONVERT_FROM_PY = None
    _CONVERT_TO_PY = None
    _DESTROY_ROS_MESSAGE = None
    _TYPE_SUPPORT = None

    __constants = {
    }

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('openarm_bimanual_planner_msgs')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'openarm_bimanual_planner_msgs.action.BimanualPlan_FeedbackMessage')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__action__bimanual_plan__feedback_message
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__action__bimanual_plan__feedback_message
            cls._CONVERT_TO_PY = module.convert_to_py_msg__action__bimanual_plan__feedback_message
            cls._TYPE_SUPPORT = module.type_support_msg__action__bimanual_plan__feedback_message
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__action__bimanual_plan__feedback_message

            from openarm_bimanual_planner_msgs.action import BimanualPlan
            if BimanualPlan.Feedback.__class__._TYPE_SUPPORT is None:
                BimanualPlan.Feedback.__class__.__import_type_support__()

            from unique_identifier_msgs.msg import UUID
            if UUID.__class__._TYPE_SUPPORT is None:
                UUID.__class__.__import_type_support__()

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class BimanualPlan_FeedbackMessage(metaclass=Metaclass_BimanualPlan_FeedbackMessage):
    """Message class 'BimanualPlan_FeedbackMessage'."""

    __slots__ = [
        '_goal_id',
        '_feedback',
    ]

    _fields_and_field_types = {
        'goal_id': 'unique_identifier_msgs/UUID',
        'feedback': 'openarm_bimanual_planner_msgs/BimanualPlan_Feedback',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.NamespacedType(['unique_identifier_msgs', 'msg'], 'UUID'),  # noqa: E501
        rosidl_parser.definition.NamespacedType(['openarm_bimanual_planner_msgs', 'action'], 'BimanualPlan_Feedback'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        from unique_identifier_msgs.msg import UUID
        self.goal_id = kwargs.get('goal_id', UUID())
        from openarm_bimanual_planner_msgs.action._bimanual_plan import BimanualPlan_Feedback
        self.feedback = kwargs.get('feedback', BimanualPlan_Feedback())

    def __repr__(self):
        typename = self.__class__.__module__.split('.')
        typename.pop()
        typename.append(self.__class__.__name__)
        args = []
        for s, t in zip(self.__slots__, self.SLOT_TYPES):
            field = getattr(self, s)
            fieldstr = repr(field)
            # We use Python array type for fields that can be directly stored
            # in them, and "normal" sequences for everything else.  If it is
            # a type that we store in an array, strip off the 'array' portion.
            if (
                isinstance(t, rosidl_parser.definition.AbstractSequence) and
                isinstance(t.value_type, rosidl_parser.definition.BasicType) and
                t.value_type.typename in ['float', 'double', 'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64']
            ):
                if len(field) == 0:
                    fieldstr = '[]'
                else:
                    assert fieldstr.startswith('array(')
                    prefix = "array('X', "
                    suffix = ')'
                    fieldstr = fieldstr[len(prefix):-len(suffix)]
            args.append(s[1:] + '=' + fieldstr)
        return '%s(%s)' % ('.'.join(typename), ', '.join(args))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.goal_id != other.goal_id:
            return False
        if self.feedback != other.feedback:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def goal_id(self):
        """Message field 'goal_id'."""
        return self._goal_id

    @goal_id.setter
    def goal_id(self, value):
        if __debug__:
            from unique_identifier_msgs.msg import UUID
            assert \
                isinstance(value, UUID), \
                "The 'goal_id' field must be a sub message of type 'UUID'"
        self._goal_id = value

    @builtins.property
    def feedback(self):
        """Message field 'feedback'."""
        return self._feedback

    @feedback.setter
    def feedback(self, value):
        if __debug__:
            from openarm_bimanual_planner_msgs.action._bimanual_plan import BimanualPlan_Feedback
            assert \
                isinstance(value, BimanualPlan_Feedback), \
                "The 'feedback' field must be a sub message of type 'BimanualPlan_Feedback'"
        self._feedback = value


class Metaclass_BimanualPlan(type):
    """Metaclass of action 'BimanualPlan'."""

    _TYPE_SUPPORT = None

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('openarm_bimanual_planner_msgs')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'openarm_bimanual_planner_msgs.action.BimanualPlan')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._TYPE_SUPPORT = module.type_support_action__action__bimanual_plan

            from action_msgs.msg import _goal_status_array
            if _goal_status_array.Metaclass_GoalStatusArray._TYPE_SUPPORT is None:
                _goal_status_array.Metaclass_GoalStatusArray.__import_type_support__()
            from action_msgs.srv import _cancel_goal
            if _cancel_goal.Metaclass_CancelGoal._TYPE_SUPPORT is None:
                _cancel_goal.Metaclass_CancelGoal.__import_type_support__()

            from openarm_bimanual_planner_msgs.action import _bimanual_plan
            if _bimanual_plan.Metaclass_BimanualPlan_SendGoal._TYPE_SUPPORT is None:
                _bimanual_plan.Metaclass_BimanualPlan_SendGoal.__import_type_support__()
            if _bimanual_plan.Metaclass_BimanualPlan_GetResult._TYPE_SUPPORT is None:
                _bimanual_plan.Metaclass_BimanualPlan_GetResult.__import_type_support__()
            if _bimanual_plan.Metaclass_BimanualPlan_FeedbackMessage._TYPE_SUPPORT is None:
                _bimanual_plan.Metaclass_BimanualPlan_FeedbackMessage.__import_type_support__()


class BimanualPlan(metaclass=Metaclass_BimanualPlan):

    # The goal message defined in the action definition.
    from openarm_bimanual_planner_msgs.action._bimanual_plan import BimanualPlan_Goal as Goal
    # The result message defined in the action definition.
    from openarm_bimanual_planner_msgs.action._bimanual_plan import BimanualPlan_Result as Result
    # The feedback message defined in the action definition.
    from openarm_bimanual_planner_msgs.action._bimanual_plan import BimanualPlan_Feedback as Feedback

    class Impl:

        # The send_goal service using a wrapped version of the goal message as a request.
        from openarm_bimanual_planner_msgs.action._bimanual_plan import BimanualPlan_SendGoal as SendGoalService
        # The get_result service using a wrapped version of the result message as a response.
        from openarm_bimanual_planner_msgs.action._bimanual_plan import BimanualPlan_GetResult as GetResultService
        # The feedback message with generic fields which wraps the feedback message.
        from openarm_bimanual_planner_msgs.action._bimanual_plan import BimanualPlan_FeedbackMessage as FeedbackMessage

        # The generic service to cancel a goal.
        from action_msgs.srv._cancel_goal import CancelGoal as CancelGoalService
        # The generic message for get the status of a goal.
        from action_msgs.msg._goal_status_array import GoalStatusArray as GoalStatusMessage

    def __init__(self):
        raise NotImplementedError('Action classes can not be instantiated')
