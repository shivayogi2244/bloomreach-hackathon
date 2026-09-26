from app.shopify_tool import _gql

data = _gql("""
query {
  customers(first: 5) {
    nodes { id email }
  }
}
""")
print(data)