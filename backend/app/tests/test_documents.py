def test_upload_document_as_admin_and_filter(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.post(
        "/api/documents",
        headers=headers,
        data={
            "title": "产品手册",
            "file_type": "pdf",
            "business_type": "product_material",
            "source_type": "internal_product_doc",
            "trust_level": "5",
            "permission_scope": "internal",
            "product_id": "P-100",
        },
        files={"file": ("manual.pdf", b"hello", "application/pdf")},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "uploaded"

    listing = client.get(
        "/api/documents?product_id=P-100&trust_level=5",
        headers=headers,
    )
    assert listing.status_code == 200
    payload = listing.json()
    assert payload["total"] == 1
    assert payload["items"][0]["title"] == "产品手册"

    detail = client.get(f"/api/documents/{payload['items'][0]['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["versions"][0]["file_size"] == 5


def test_business_user_cannot_upload(client, business_token):
    response = client.post(
        "/api/documents",
        headers={"Authorization": f"Bearer {business_token}"},
        data={
            "title": "销售 FAQ",
            "file_type": "txt",
            "business_type": "sales_faq",
            "source_type": "internal_sales_doc",
            "trust_level": "3",
            "permission_scope": "internal",
        },
        files={"file": ("faq.txt", b"faq", "text/plain")},
    )
    assert response.status_code == 403
