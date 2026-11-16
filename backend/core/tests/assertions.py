def assert_validation_error(response, attribute, code):
	assert response.status_code == 400
	assert response.data['type'] == 'validation_error'
	assert len(response.data['errors']) == 1

	error = response.data['errors'][0]
	assert set(error) == {'attr', 'code', 'detail'}
	assert error['attr'] == attribute
	assert error['code'] == code
	assert isinstance(error['detail'], str)
	assert error['detail']
