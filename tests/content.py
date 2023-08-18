from hypothesis import given, strategies

byte_content = given(content=strategies.binary())
