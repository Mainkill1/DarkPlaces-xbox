/* Small CRT surface declared but not implemented by the pinned nxdk PDCLib. */

double atof(const char *text)
{
	double value = 0.0;
	double fraction = 0.1;
	double scale = 1.0;
	int negative = 0;
	int exponent = 0;
	int exponent_negative = 0;

	if (!text)
		return 0.0;
	while (*text == ' ' || *text == '\t' || *text == '\r' || *text == '\n' || *text == '\f' || *text == '\v')
		++text;
	if (*text == '-' || *text == '+')
	{
		negative = *text == '-';
		++text;
	}
	while (*text >= '0' && *text <= '9')
	{
		value = value * 10.0 + (double)(*text - '0');
		++text;
	}
	if (*text == '.')
	{
		++text;
		while (*text >= '0' && *text <= '9')
		{
			value += (double)(*text - '0') * fraction;
			fraction *= 0.1;
			++text;
		}
	}
	if (*text == 'e' || *text == 'E')
	{
		++text;
		if (*text == '-' || *text == '+')
		{
			exponent_negative = *text == '-';
			++text;
		}
		while (*text >= '0' && *text <= '9')
		{
			if (exponent < 1000)
				exponent = exponent * 10 + (*text - '0');
			++text;
		}
	}
	while (exponent-- > 0)
		scale *= 10.0;
	value = exponent_negative ? value / scale : value * scale;
	return negative ? -value : value;
}
