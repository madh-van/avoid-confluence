import pypandoc


def get_jira_markup(source: str, input_format: str = "org") -> str:
    return pypandoc.convert_text(source=source, to="jira", format=input_format)
    # TODO toc and other options to explore ?
    # extra_args=['-V',
    # 'geometry:margin=1.5cm'
    # ]
