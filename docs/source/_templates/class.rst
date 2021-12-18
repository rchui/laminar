{{ objname | escape | underline}}

.. autoclass:: {{ fullname }}
    :members:
    :inherited-members: BaseModel
    :show-inheritance:

    {% block methods %}
    {% if methods %}
    .. rubric:: {{ _('Methods') }}

    .. autosummary::
        :nosignatures:
    {% for item in methods %}
        {% if not item.startswith('_') %}
        ~{{ fullname }}.{{ item }}
        {% endif %}
    {%- endfor %}
    {% endif %}
    {% endblock %}

    {% block attributes %}
    {% if attributes %}
    .. rubric:: {{ _('Attributes') }}

    .. autosummary::
        :nosignatures:
    {% for item in attributes %}
        {% if not item.startswith('_') %}
        ~{{ fullname }}.{{ item }}
        {% endif %}
    {%- endfor %}
    {% endif %}
    {% endblock %}
